#!/usr/bin/env python3

import rospy
import tf
import numpy as np
import cv2
from cv_bridge import CvBridge, CvBridgeError

# ROS Messages
from gazebo_msgs.msg import ModelStates
from sensor_msgs.msg import CameraInfo, Image
from darknet_ros_msgs.msg import BoundingBoxes, BoundingBox
from geometry_msgs.msg import Pose
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

class YoloDetectorSim:
    def __init__(self):
        rospy.init_node('yolo_detector_sim')

        # Dictionary of models to track and detect
        # Structure: 'model_name_in_gazebo': ('class_name', size_x, size_y, size_z)
        self.targets = {
            'washer_box_a_front_open': ('washing machine box', 0.6, 0.6, 0.6),
            'basket_box_b_open_top': ('laundry basket', 0.5, 0.5, 0.4)
        }

        self.camera_info = None
        self.tf_listener = tf.TransformListener()
        self.bridge = CvBridge()
        self.cv_image = None

        # Subscribers
        self.cam_info_sub = rospy.Subscriber('/xtion/rgb/camera_info', CameraInfo, self.cam_info_cb)
        self.image_sub = rospy.Subscriber('/xtion/rgb/image_raw', Image, self.image_cb)
        self.model_states_sub = rospy.Subscriber('/gazebo/model_states', ModelStates, self.model_states_cb)

        # Publishers
        self.bbox_pub = rospy.Publisher('/darknet_ros/bounding_boxes', BoundingBoxes, queue_size=1)
        self.head_pub = rospy.Publisher('/head_controller/command', JointTrajectory, queue_size=1)

        # Automatically trigger head tilt down to face the boxes after 2.0s
        rospy.Timer(rospy.Duration(2.0), self.tilt_head, oneshot=True)

        rospy.loginfo("YoloDetectorSim initialized successfully.")

    def cam_info_cb(self, msg):
        self.camera_info = msg

    def image_cb(self, msg):
        try:
            self.cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except CvBridgeError as e:
            rospy.logerr(f"CvBridge Error: {e}")

    def tilt_head(self, event):
        rospy.loginfo("Sensing simulation started. Automatic head controller: tilting robot head downwards...")
        traj = JointTrajectory()
        traj.joint_names = ['head_1_joint', 'head_2_joint']
        point = JointTrajectoryPoint()
        point.positions = [0.0, -0.7] # 0.0 pan (straight), -0.7 tilt (downward)
        point.velocities = [0.0, 0.0]
        point.time_from_start = rospy.Duration(1.5)
        traj.points.append(point)
        self.head_pub.publish(traj)

    def get_corners(self, size_x, size_y, size_z):
        # Generate 8 corners of a 3D bounding box centered at origin
        x = size_x / 2.0
        y = size_y / 2.0
        z = size_z / 2.0
        return np.array([
            [-x, -y, -z],
            [ x, -y, -z],
            [-x,  y, -z],
            [ x,  y, -z],
            [-x, -y,  z],
            [ x, -y,  z],
            [-x,  y,  z],
            [ x,  y,  z]
        ])

    def pose_to_matrix(self, pose):
        # Convert pose message to 4x4 transform matrix
        q = [pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w]
        t = [pose.position.x, pose.position.y, pose.position.z]
        
        T = tf.transformations.quaternion_matrix(q)
        T[0:3, 3] = t
        return T

    def model_states_cb(self, msg):
        if self.camera_info is None:
            return

        # Find the robot name in model states
        robot_name = None
        for name in msg.name:
            if name.startswith('tiago'):
                robot_name = name
                break
        
        if robot_name is None:
            rospy.logdebug("Robot model not found in Gazebo states.")
            return

        # Width and height from camera info
        width = self.camera_info.width
        height = self.camera_info.height
        
        # Camera matrix K
        K = np.array(self.camera_info.K).reshape((3, 3))
        fx = K[0, 0]
        fy = K[1, 1]
        cx = K[0, 2]
        cy = K[1, 2]

        camera_frame = self.camera_info.header.frame_id
        # Transform from camera frame to robot base frame (base_footprint)
        base_frame = 'base_footprint'
        
        try:
            self.tf_listener.waitForTransform(camera_frame, base_frame, rospy.Time(0), rospy.Duration(1.0))
            (trans, rot) = self.tf_listener.lookupTransform(camera_frame, base_frame, rospy.Time(0))
            T_base_cam = tf.transformations.quaternion_matrix(rot)
            T_base_cam[0:3, 3] = trans
        except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException) as e:
            rospy.logdebug(f"TF lookup failed for camera to base: {e}")
            return

        # Get robot pose in the Gazebo world frame
        idx_robot = msg.name.index(robot_name)
        pose_robot = msg.pose[idx_robot]
        T_robot_world = self.pose_to_matrix(pose_robot)
        T_world_robot = tf.transformations.inverse_matrix(T_robot_world)

        # Full transform from world to camera frame: T_world_cam = T_base_cam * T_world_robot
        T_world_cam = np.dot(T_base_cam, T_world_robot)

        bbox_msg = BoundingBoxes()
        bbox_msg.header.stamp = rospy.Time.now()
        bbox_msg.header.frame_id = camera_frame
        bbox_msg.image_header.stamp = rospy.Time.now()
        bbox_msg.image_header.frame_id = camera_frame

        # Loop through all models in Gazebo state
        for name, (cls_name, sx, sy, sz) in self.targets.items():
            if name in msg.name:
                idx = msg.name.index(name)
                pose = msg.pose[idx]
                
                # Transform matrix from model to world
                T_model_world = self.pose_to_matrix(pose)
                
                # Full transform from model to camera
                T_model_cam = np.dot(T_world_cam, T_model_world)
                
                # Get model corners
                corners = self.get_corners(sx, sy, sz)
                
                # Transform corners to camera frame
                corners_cam = []
                for pt in corners:
                    pt_h = np.array([pt[0], pt[1], pt[2], 1.0])
                    pt_cam = np.dot(T_model_cam, pt_h)
                    corners_cam.append(pt_cam[0:3])
                
                # Project corners to image coordinates
                u_pts = []
                v_pts = []
                in_front = False
                
                for pt in corners_cam:
                    # pt is [x, y, z] in camera optical frame (z is depth, x is right, y is down)
                    if pt[2] > 0.1: # Point is in front of the camera
                        in_front = True
                        u = (pt[0] * fx / pt[2]) + cx
                        v = (pt[1] * fy / pt[2]) + cy
                        u_pts.append(u)
                        v_pts.append(v)
                
                # If model is visible (at least some corners are in front of camera)
                if in_front and len(u_pts) > 0:
                    xmin = max(0, int(min(u_pts)))
                    xmax = min(width - 1, int(max(u_pts)))
                    ymin = max(0, int(min(v_pts)))
                    ymax = min(height - 1, int(max(v_pts)))
                    
                    # Check if bounding box is reasonably sized (not off-screen completely)
                    if xmax > xmin and ymax > ymin:
                        bbox = BoundingBox()
                        bbox.probability = 0.95
                        bbox.xmin = xmin
                        bbox.xmax = xmax
                        bbox.ymin = ymin
                        bbox.ymax = ymax
                        bbox.id = len(bbox_msg.bounding_boxes)
                        bbox.Class = cls_name
                        bbox_msg.bounding_boxes.append(bbox)

        # Publish the bounding boxes
        if len(bbox_msg.bounding_boxes) > 0:
            self.bbox_pub.publish(bbox_msg)

        # Create window displaying what the robot is seeing in the moment (drawing bounding boxes on the camera stream)
        if self.cv_image is not None:
            img_display = self.cv_image.copy()
            for bbox in bbox_msg.bounding_boxes:
                cv2.rectangle(img_display, (bbox.xmin, bbox.ymin), (bbox.xmax, bbox.ymax), (0, 255, 0), 2)
                cv2.putText(img_display, f"{bbox.Class} ({bbox.probability:.2f})", 
                            (bbox.xmin, bbox.ymin - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.imshow("TIAGo Camera View (YOLO Detections)", img_display)
            cv2.waitKey(1)

if __name__ == '__main__':
    try:
        node = YoloDetectorSim()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
