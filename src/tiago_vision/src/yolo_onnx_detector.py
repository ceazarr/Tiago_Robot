#!/usr/bin/env python3

import rospy
import tf
import numpy as np
import cv2
import message_filters
import os
from cv_bridge import CvBridge, CvBridgeError

from ultralytics import YOLO

from sensor_msgs.msg import Image, PointCloud2
from sensor_msgs import point_cloud2
from geometry_msgs.msg import PointStamped
from std_srvs.srv import Trigger, TriggerResponse


class YoloOnnxDetector:
    def __init__(self):
        rospy.init_node('yolo_onnx_detector', anonymous=True)

        # Parameters
        self.model_path = rospy.get_param('~model_path', '/tiago_workspace/best.pt')
        self.conf_threshold = rospy.get_param('~conf_threshold', 0.5)
        self.iou_threshold = rospy.get_param('~iou_threshold', 0.45)
        self.target_frame = rospy.get_param('~target_frame', 'base_footprint')
        self.image_topic = rospy.get_param('~image_topic', '/xtion/rgb/high_res/image_raw')
        self.point_cloud_topic = rospy.get_param('~point_cloud_topic', '/xtion/depth_registered/points')

        # Load Model
        rospy.loginfo(f"Loading YOLO model from: {self.model_path}")
        if not os.path.exists(self.model_path):
            rospy.logerr(f"Model file not found at {self.model_path}!")
            rospy.signal_shutdown("Model not found")
            return

        try:
            self.model = YOLO(self.model_path, task='segment')
            print(type(self.model.model))
            print(self.model.model)
            self.classes = self.model.names 
            rospy.loginfo(f"Model loaded! Classes: {self.classes}")
        except Exception as e:
            rospy.logerr(f"Failed to load YOLO model: {e}")
            raise e

        # Color mapping
        self.class_colors = {}
        for c_id, c_name in self.classes.items():
            if c_name == 'cloth': 
                self.class_colors[c_id] = (0, 255, 0)
            elif c_name == 'boxA': 
                self.class_colors[c_id] = (0, 0, 255)
            elif c_name == 'boxB': 
                self.class_colors[c_id] = (255, 0, 0)
            else: 
                self.class_colors[c_id] = (255, 255, 255)

        self.tf_listener = tf.TransformListener()
        self.bridge = CvBridge()

        # Publishers
        self.grasp_pub = rospy.Publisher('/tiago_vision/clothes_grasp_target', PointStamped, queue_size=1)
        self.drop_pub = rospy.Publisher('/tiago_vision/clothes_drop_target', PointStamped, queue_size=1)
        self.box_a_target_pub = rospy.Publisher('/tiago_vision/box_a_target', PointStamped, queue_size=1)
        self.box_b_target_pub = rospy.Publisher('/tiago_vision/box_b_target', PointStamped, queue_size=1)
        self.box_a_cloud_pub = rospy.Publisher('/tiago_vision/box_a_cloud', PointCloud2, queue_size=1)
        self.box_b_cloud_pub = rospy.Publisher('/tiago_vision/box_b_cloud', PointCloud2, queue_size=1)
        
        # CRITICAL: OctoMap publisher for MoveIt collision avoidance
        self.octomap_pub = rospy.Publisher('/moveit/filtered_box_points', PointCloud2, queue_size=1)
        
        self.debug_img_pub = rospy.Publisher('/tiago_vision/yolo_debug_image', Image, queue_size=1)

        # Mode
        self.continuous_mode = rospy.get_param('~continuous_mode', False)
        self.process_next = True if self.continuous_mode else False
        
        # Trigger service
        self.trigger_srv = rospy.Service('/tiago_vision/trigger_detection', Trigger, self.trigger_callback)

        # Synchronized subscribers
        image_sub = message_filters.Subscriber(self.image_topic, Image)
        pc_sub = message_filters.Subscriber(self.point_cloud_topic, PointCloud2)
        
        ts = message_filters.ApproximateTimeSynchronizer([image_sub, pc_sub], queue_size=30, slop=5.0)
        ts.registerCallback(self.callback)

        rospy.loginfo("YoloNativeDetector node initialized and listening.")

    def trigger_callback(self, req):
        self.process_next = True
        rospy.loginfo("Detection triggered!")
        return TriggerResponse(success=True, message="Detection triggered.")

    def callback(self, img_msg, pc_msg):
        rospy.loginfo_throttle(2, "Synchronizer successfully matched an image and cloud!")
        if not self.process_next:
            return
            
        if not self.continuous_mode:
            self.process_next = False

        try:
            cv_image = self.bridge.imgmsg_to_cv2(img_msg, "bgr8")
        except CvBridgeError as e:
            rospy.logerr(f"CvBridge Error: {e}")
            return

        # Ensure base image is clean uint8
        if cv_image.dtype != np.uint8:
            cv_image = cv_image.astype(np.uint8)
        
        debug_image = cv_image.copy()

        # YOLO Inference
        results = self.model.predict(
            source=cv_image, 
            conf=self.conf_threshold, 
            iou=self.iou_threshold, 
            retina_masks=True, 
            verbose=False
        )[0]

        if results.masks is None or results.boxes is None:
            self.publish_debug_image(debug_image)
            return

        # Extract detections
        detections = []
        classes = results.boxes.cls.cpu().numpy().astype(int)
        confs = results.boxes.conf.cpu().numpy()
        bboxes = results.boxes.xyxy.cpu().numpy().astype(int)
        masks = results.masks.data.cpu().numpy()

        for i in range(len(classes)):
            cls_id = classes[i]
            label = self.classes.get(cls_id, f"class_{cls_id}")
            color = self.class_colors.get(cls_id, (255, 255, 255))
            binary_mask = (masks[i] > 0.5).astype(np.uint8)

            detections.append({
                'label': label,
                'binary_mask': binary_mask,
                'bbox': bboxes[i],
                'conf': confs[i],
                'color': color
            })

        # --- HOLLOW BOX LOGIC: Subtract cloth from boxes ---
        cloth_mask = np.zeros(cv_image.shape[:2], dtype=np.uint8)
        for det in detections:
            if det['label'] == 'cloth':
                cloth_mask = cv2.bitwise_or(cloth_mask, det['binary_mask'])
                
        for det in detections:
            if det['label'] in ['boxA', 'boxB']:
                det['binary_mask'] = cv2.bitwise_and(det['binary_mask'], cv2.bitwise_not(cloth_mask))

        # --- SAFE DEBUG DRAWING ---
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            color = det['color']
            
            # Bounding box
            cv2.rectangle(debug_image, (x1, y1), (x2, y2), color, 2)
            cv2.putText(debug_image, f"{det['label']} ({det['conf']:.2f})", 
                       (x1, max(y1 - 10, 0)), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Mask overlay - SAFE: create separate overlay, ensure uint8
            overlay = debug_image.copy()
            mask_idx = det['binary_mask'] > 0
            overlay[mask_idx] = color
            # addWeighted requires same dtype and channels
            debug_image = cv2.addWeighted(overlay, 0.3, debug_image, 0.7, 0)

        # PointCloud processing
        xyz_array = self.pointcloud2_to_numpy(pc_msg)
        if xyz_array is None:
            self.publish_debug_image(debug_image)
            return

        R, t = self.get_tf_transform(pc_msg)
        if R is None:
            self.publish_debug_image(debug_image)
            return

        # Aggregate all box wall points for OctoMap
        all_box_wall_points = []

        for det in detections:
            pts_base = self.mask_to_cloud(det['binary_mask'], xyz_array, R, t, det['label'])
            if pts_base is None:
                continue

            target_msg = self.compute_target(det['label'], pts_base, pc_msg.header)
            self.publish_results(det['label'], target_msg, pts_base, pc_msg.header.stamp)

            # Collect box wall points for OctoMap (hollow mesh = walls only, no cloth)
            if det['label'] in ['boxA', 'boxB']:
                all_box_wall_points.append(pts_base)

        # Publish combined hollow box point cloud for MoveIt OctoMap
        if all_box_wall_points:
            combined_walls = np.vstack(all_box_wall_points)
            self._publish_masked_cloud(combined_walls, self.octomap_pub, pc_msg.header.stamp)
            rospy.loginfo_throttle(5, f"Published {len(combined_walls)} wall points to OctoMap")

        self.publish_debug_image(debug_image)

    def pointcloud2_to_numpy(self, pc_msg):
        if not pc_msg.data:
            return None
        
        try:
            x_offset = next(f.offset for f in pc_msg.fields if f.name == 'x')
            y_offset = next(f.offset for f in pc_msg.fields if f.name == 'y')
            z_offset = next(f.offset for f in pc_msg.fields if f.name == 'z')
            
            dtype = np.dtype({
                'names': ['x', 'y', 'z'], 
                'formats': ['<f4', '<f4', '<f4'], 
                'offsets': [x_offset, y_offset, z_offset], 
                'itemsize': pc_msg.point_step
            })
            
            cloud_arr = np.ndarray(
                shape=(pc_msg.width * pc_msg.height,), 
                dtype=dtype, 
                buffer=pc_msg.data
            )
            
            xyz = np.stack([cloud_arr['x'], cloud_arr['y'], cloud_arr['z']], axis=-1)
            
            if pc_msg.height > 1:
                xyz = xyz.reshape((pc_msg.height, pc_msg.width, 3))
            return xyz
        except Exception as e:
            rospy.logerr(f"Failed to parse PointCloud2: {e}")
            return None

    def get_tf_transform(self, pc_msg):
        try:
            self.tf_listener.waitForTransform(
                self.target_frame, 
                pc_msg.header.frame_id, 
                pc_msg.header.stamp, 
                rospy.Duration(1.0)
            )
            trans, rot = self.tf_listener.lookupTransform(
                self.target_frame, 
                pc_msg.header.frame_id, 
                pc_msg.header.stamp
            )
            R = tf.transformations.quaternion_matrix(rot)[:3, :3]
            t = np.array(trans)
            return R, t
        except Exception as e:
            rospy.logwarn(f"TF failed: {e}")
            return None, None

    def mask_to_cloud(self, binary_mask, xyz_array, R, t, label):
        pc_h, pc_w = xyz_array.shape[:2]
        
        if binary_mask.shape[:2] != (pc_h, pc_w):
            scaled_mask = cv2.resize(binary_mask, (pc_w, pc_h), interpolation=cv2.INTER_NEAREST)
        else:
            scaled_mask = binary_mask

        pts_3d = xyz_array[scaled_mask > 0]
        pts_3d = pts_3d[~np.isnan(pts_3d).any(axis=1)]
        
        if len(pts_3d) == 0:
            return None

        pts_base = pts_3d @ R.T + t
        return pts_base

    def compute_target(self, label, pts_base, header):
        point_base = PointStamped()
        point_base.header.frame_id = self.target_frame
        point_base.header.stamp = header.stamp

        if label == 'cloth':
            top_point = pts_base[np.argmax(pts_base[:, 2])]
            point_base.point.x, point_base.point.y, point_base.point.z = top_point.tolist()
        elif label in ['boxA', 'boxB']:
            centroid = pts_base.mean(axis=0)
            point_base.point.x, point_base.point.y, point_base.point.z = centroid.tolist()

        return point_base

    def publish_results(self, label, point_base, pts_base, stamp):
        if label == 'cloth':
            self.grasp_pub.publish(point_base)
            rospy.loginfo_throttle(2, 
                f"Grasp target: [{point_base.point.x:.3f}, {point_base.point.y:.3f}, {point_base.point.z:.3f}]")
        elif label == 'boxB':
            self.drop_pub.publish(point_base)
            self._publish_masked_cloud(pts_base, self.box_b_cloud_pub, stamp)
            rospy.loginfo_throttle(2, 
                f"Drop target (boxB): [{point_base.point.x:.3f}, {point_base.point.y:.3f}, {point_base.point.z:.3f}]")
        elif label == 'boxA':
            self.box_a_target_pub.publish(point_base)
            self._publish_masked_cloud(pts_base, self.box_a_cloud_pub, stamp)
            rospy.loginfo_throttle(2, 
                f"Box A target: [{point_base.point.x:.3f}, {point_base.point.y:.3f}, {point_base.point.z:.3f}]")

    def _publish_masked_cloud(self, pts_base, publisher, stamp):
        if len(pts_base) == 0:
            return
        cloud_msg = point_cloud2.create_cloud_xyz32(
            header=rospy.Header(frame_id=self.target_frame, stamp=stamp),
            points=pts_base.tolist(),
        )
        publisher.publish(cloud_msg)

    def publish_debug_image(self, image):
        try:
            msg = self.bridge.cv2_to_imgmsg(image, encoding="bgr8")
            self.debug_img_pub.publish(msg)
        except Exception:
            # Fallback when cv_bridge has version mismatch key errors (e.g. KeyError: 16)
            from sensor_msgs.msg import Image as RosImage
            msg = RosImage()
            msg.header.stamp = rospy.Time.now()
            msg.header.frame_id = self.target_frame
            msg.height = image.shape[0]
            msg.width = image.shape[1]
            msg.encoding = "bgr8"
            msg.is_bigendian = False
            msg.step = image.shape[1] * 3
            msg.data = image.tobytes()
            self.debug_img_pub.publish(msg)

if __name__ == '__main__':
    try:
        YoloOnnxDetector()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass