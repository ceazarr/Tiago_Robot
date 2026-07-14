##!/usr/bin/env python3
#
#import sys
#import rospy
#import moveit_commander
#
#from geometry_msgs.msg import PointStamped, PoseStamped, Twist
#from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
#
#
#class LaundryManipulationNode:
#    def __init__(self):
#        rospy.init_node("laundry_manipulation_node")
#
#        self.latest_grasp = None
#        self.latest_drop = None
#        self.executing = False
#
#        self.drive_speed = rospy.get_param("~drive_speed", 0.05)
#        self.turn_speed = rospy.get_param("~turn_speed", 0.25)
#        self.turn_90_duration = rospy.get_param("~turn_90_duration", 6.28)
#        self.box_distance = rospy.get_param("~box_distance", 0.72)
#        self.target_frame = rospy.get_param("~target_frame", "base_footprint")
#
#        rospy.Subscriber("/tiago_vision/clothes_grasp_target", PointStamped, self.grasp_cb)
#        rospy.Subscriber("/tiago_vision/clothes_drop_target", PointStamped, self.drop_cb)
#
#        self.cmd_vel_pub = rospy.Publisher("/mobile_base_controller/cmd_vel", Twist, queue_size=1)
#        self.gripper_pub = rospy.Publisher("/gripper_controller/command", JointTrajectory, queue_size=1)
#
#        moveit_commander.roscpp_initialize(sys.argv)
#        self.arm = moveit_commander.MoveGroupCommander("arm_torso")
#        self.arm.set_planning_time(20.0)
#        self.arm.set_num_planning_attempts(10)
#        self.arm.set_max_velocity_scaling_factor(0.3)
#        self.arm.set_max_acceleration_scaling_factor(0.3)
#        self.arm.set_goal_position_tolerance(0.03)
#        self.arm.set_goal_orientation_tolerance(0.30)
#
#        rospy.loginfo("Laundry manipulation node initialized.")
#
#    def grasp_cb(self, msg):
#        if not self.executing:
#            self.latest_grasp = msg
#
#    def drop_cb(self, msg):
#        if not self.executing:
#            self.latest_drop = msg
#
#    def stop_base(self):
#        self.cmd_vel_pub.publish(Twist())
#        rospy.sleep(0.5)
#
#    def drive_for_time(self, linear_x, duration):
#        cmd = Twist()
#        cmd.linear.x = linear_x
#        rate = rospy.Rate(10)
#        start = rospy.Time.now()
#
#        while (rospy.Time.now() - start).to_sec() < duration and not rospy.is_shutdown():
#            self.cmd_vel_pub.publish(cmd)
#            rate.sleep()
#
#        self.stop_base()
#
#    def turn_for_time(self, angular_z, duration):
#        cmd = Twist()
#        cmd.angular.z = angular_z
#        rate = rospy.Rate(10)
#        start = rospy.Time.now()
#
#        while (rospy.Time.now() - start).to_sec() < duration and not rospy.is_shutdown():
#            self.cmd_vel_pub.publish(cmd)
#            rate.sleep()
#
#        self.stop_base()
#
#    def turn_left_90(self):
#        rospy.loginfo("Turning left 90 degrees...")
#        self.turn_for_time(abs(self.turn_speed), self.turn_90_duration)
#
#    def turn_right_90(self):
#        rospy.loginfo("Turning right 90 degrees...")
#        self.turn_for_time(-abs(self.turn_speed), self.turn_90_duration)
#
#    def drive_forward_distance(self, distance):
#
#        if abs(distance) < 1e-4:
#            return
#
#        duration = abs(distance) / self.drive_speed
#
#        speed = self.drive_speed if distance > 0 else -self.drive_speed
#
#        rospy.loginfo(
#            "Driving %.3f m", distance
#        )
#
#        self.drive_for_time(speed, duration)
#    def wait_for_target(self, target_type):
#        rospy.loginfo("Waiting for %s target...", target_type)
#        rate = rospy.Rate(10)
#
#        while not rospy.is_shutdown():
#            target = self.latest_grasp if target_type == "grasp" else self.latest_drop
#
#            if target is not None:
#                rospy.loginfo(
#                    "Got %s target: x=%.3f, y=%.3f, z=%.3f",
#                    target_type,
#                    target.point.x,
#                    target.point.y,
#                    target.point.z
#                )
#                return target
#
#            rate.sleep()
#
#        return None
#
#    def wait_for_fresh_target(self, target_type, after_time):
#        rospy.loginfo("Waiting for fresh %s target...", target_type)
#        rate = rospy.Rate(10)
#
#        while not rospy.is_shutdown():
#            target = self.latest_grasp if target_type == "grasp" else self.latest_drop
#
#            if target is not None:
#                if target.header.stamp >= after_time:
#                    rospy.loginfo(
#                        "Got fresh %s target: x=%.3f, y=%.3f, z=%.3f",
#                        target_type,
#                        target.point.x,
#                        target.point.y,
#                        target.point.z
#                    )
#                    return target
#
#            rate.sleep()
#
#        return None
#
#    def lateral_move_to_target_y(self, target):
#        desired_y = 0.00
#        y = target.point.y - desired_y
#
#        rospy.loginfo(
#            "Lateral correction: current y=%.3f, desired y=%.3f, moving %.3f",
#            target.point.y,
#            desired_y,
#            y
#        )
#        if abs(y) < 0.05:
#            rospy.loginfo("Target already close to y=0. No lateral move needed.")
#            return
#
#        if y > 0.0:
#            self.turn_left_90()
#            self.drive_forward_distance(abs(y))
#            self.turn_right_90()
#        else:
#            self.turn_right_90()
#            self.drive_forward_distance(abs(y))
#            self.turn_left_90()
#
#        rospy.sleep(2.0)
#
#    def move_from_box_a_to_box_b(self):
#        rospy.loginfo("Moving from Box A to Box B...")
#
#        self.turn_right_90()
#        self.drive_forward_distance(self.box_distance - 0.00)
#        # self.turn_left_90()
#        rospy.loginfo("Turning left 90 degrees...")
#        self.turn_for_time(
#            abs(self.turn_speed),
#            self.turn_90_duration * 90.0 / 90.0
#        )
#
#        rospy.sleep(2.0)
#
#    def make_pose(self, point_msg, x_offset=0.0, y_offset=0.0, z_offset=0.0):
#        pose = PoseStamped()
#
#        # Force current time and base_footprint to avoid old TF timestamp problems.
#        pose.header.frame_id = self.target_frame
#        pose.header.stamp = rospy.Time.now()
#
#        # Do not fully trust the detected z value. Sometimes the point cloud detects
#        # the box edge or the upper surface instead of the cloth center.
#        safe_z = max(min(point_msg.point.z, 0.55), 0.40)
#
#        pose.pose.position.x = point_msg.point.x + x_offset
#        pose.pose.position.y = point_msg.point.y + y_offset
#        pose.pose.position.z = safe_z + z_offset
#
#        # Keep the same simple orientation, but the orientation tolerance above is relaxed.
#        pose.pose.orientation.x = 0.0
#        pose.pose.orientation.y = 0.0
#        pose.pose.orientation.z = 0.0
#        pose.pose.orientation.w = 1.0
#
#        return pose
#
#    def move_to_pose(self, pose, label):
#        rospy.loginfo("Moving to %s...", label)
#
#        self.arm.set_pose_target(pose)
#        success = self.arm.go(wait=True)
#
#        self.arm.stop()
#        self.arm.clear_pose_targets()
#
#        if success:
#            rospy.loginfo("Reached %s.", label)
#        else:
#            rospy.logwarn("Failed to reach %s.", label)
#
#        return success
#
#    def send_gripper_command(self, finger_position):
#        traj = JointTrajectory()
#        traj.joint_names = [
#            "gripper_left_finger_joint",
#            "gripper_right_finger_joint"
#        ]
#
#        point = JointTrajectoryPoint()
#        point.positions = [finger_position, finger_position]
#        point.velocities = [0.0, 0.0]
#        point.time_from_start = rospy.Duration(1.0)
#
#        traj.points.append(point)
#        self.gripper_pub.publish(traj)
#
#    def open_gripper(self):
#        rospy.loginfo("Opening gripper...")
#        self.send_gripper_command(0.045)
#        rospy.sleep(1.5)
#
#    def close_gripper(self):
#        rospy.loginfo("Closing gripper...")
#        self.send_gripper_command(0.0)
#        rospy.sleep(1.5)
#
#    def move_arm_to_carry_pose(self):
#        rospy.loginfo("Moving arm to carry pose...")
#
#        joint_goal = {
#            "torso_lift_joint": 0.15,
#            "arm_1_joint": 0.20,
#            "arm_2_joint": -1.30,
#            "arm_3_joint": -0.20,
#            "arm_4_joint": 1.90,
#            "arm_5_joint": -1.57,
#            "arm_6_joint": 1.30,
#            "arm_7_joint": 0.00,
#        }
#
#        self.arm.set_joint_value_target(joint_goal)
#        success = self.arm.go(wait=True)
#        self.arm.stop()
#
#        if success:
#            rospy.loginfo("Reached carry pose.")
#        else:
#            rospy.logwarn("Failed to reach carry pose.")
#
#        return success
#
#    def pick_cloth(self, grasp_target):
#        rospy.loginfo(
#            "Raw grasp target: x=%.3f, y=%.3f, z=%.3f",
#            grasp_target.point.x,
#            grasp_target.point.y,
#            grasp_target.point.z
#        )
#
#        # Front-insertion grasp strategy:
#        # pre_grasp is outside Box A, grasp only moves forward along x.
#        # This avoids the previous top-down motion that can collide with the box rim.
#        pre_grasp = self.make_pose(grasp_target, x_offset=-0.22, z_offset=0.03)
#        grasp = self.make_pose(grasp_target, x_offset=-0.08, z_offset=0.03)
#        lift = self.make_pose(grasp_target, x_offset=-0.18, z_offset=0.18)
#
#        rospy.loginfo(
#            "Safe pre-grasp: x=%.3f, y=%.3f, z=%.3f",
#            pre_grasp.pose.position.x,
#            pre_grasp.pose.position.y,
#            pre_grasp.pose.position.z
#        )
#        rospy.loginfo(
#            "Safe grasp: x=%.3f, y=%.3f, z=%.3f",
#            grasp.pose.position.x,
#            grasp.pose.position.y,
#            grasp.pose.position.z
#        )
#
#        self.open_gripper()
#
#        if not self.move_to_pose(pre_grasp, "pre-grasp pose"):
#            return False
#
#        if not self.move_to_pose(grasp, "grasp pose"):
#            return False
#
#        self.close_gripper()
#
#        if not self.move_to_pose(lift, "lift pose"):
#            return False
#
#        self.move_arm_to_carry_pose()
#        return True
#
#    def place_cloth(self, drop_target):
#        pre_drop = self.make_pose(drop_target, z_offset=0.25)
#        drop = self.make_pose(drop_target, z_offset=0.12)
#
#        if not self.move_to_pose(pre_drop, "pre-drop pose"):
#            return False
#
#        if not self.move_to_pose(drop, "drop pose"):
#            return False
#
#        self.open_gripper()
#
#        if not self.move_to_pose(pre_drop, "retreat pose"):
#            return False
#
#        self.move_arm_to_carry_pose()
#        return True
#
#    def run(self):
#        rospy.sleep(2.0)
#
#        # 1. Read initial grasp target from middle position
#        initial_grasp = self.wait_for_target("grasp")
#        if initial_grasp is None:
#            return
#
#        # 2. Move laterally to Box A front
#        self.lateral_move_to_target_y(initial_grasp)
#
#        # 2.5 Move closer to Box A
#        self.drive_forward_distance(-0.10)
#
#        # 3. Wait for a NEW grasp target after base motion
#        self.latest_grasp = None
#        self.latest_drop = None
#        move_finish_time = rospy.Time.now()
#        rospy.sleep(2.0)
#
#        grasp_target = self.wait_for_fresh_target("grasp", move_finish_time)
#        if grasp_target is None:
#            return
#
#        self.executing = True
#
#        if not self.pick_cloth(grasp_target):
#            rospy.logwarn("Pick cloth failed.")
#            self.executing = False
#            return
#
#        self.executing = False
#        rospy.sleep(1.0)
#
#        # 4. Move from Box A to Box B
#        self.move_from_box_a_to_box_b()
#        self.drive_forward_distance(0.20)
#
#        # 5. Wait for a NEW drop target after base motion
#        self.latest_grasp = None
#        self.latest_drop = None
#        move_finish_time = rospy.Time.now()
#        rospy.sleep(2.0)
#
#        drop_target = self.wait_for_fresh_target("drop", move_finish_time)
#        if drop_target is None:
#            return
#
#        self.executing = True
#
#        if not self.place_cloth(drop_target):
#            rospy.logwarn("Place cloth failed.")
#            self.executing = False
#            return
#
#        self.executing = False
#        self.stop_base()
#
#        rospy.loginfo("Laundry pick-and-place task completed.")
#        rospy.spin()
#
#
#if __name__ == "__main__":
#    try:
#        node = LaundryManipulationNode()
#        node.run()
#    except rospy.ROSInterruptException:
#        pass
#




#!/usr/bin/env python3

#import rospy
#from geometry_msgs.msg import PointStamped, Twist
#
#class VisionTestDriver:
#    def __init__(self):
#        rospy.init_node("vision_test_driver_node")
#
#        self.latest_grasp = None
#        self.latest_drop = None
#
#        # Reusing your exact kinematic constants
#        self.drive_speed = rospy.get_param("~drive_speed", 0.05)
#        self.turn_speed = rospy.get_param("~turn_speed", 0.25)
#        self.turn_90_duration = rospy.get_param("~turn_90_duration", 6.28)
#        self.box_distance = rospy.get_param("~box_distance", 0.72)
#
#        rospy.Subscriber("/tiago_vision/box_a_center", PointStamped, self.grasp_cb)
#        rospy.Subscriber("/tiago_vision/clothes_drop_target", PointStamped, self.drop_cb)
#
#        self.cmd_vel_pub = rospy.Publisher("/mobile_base_controller/cmd_vel", Twist, queue_size=1)
#
#        rospy.loginfo("Vision Test Driver initialized. MoveIt disabled.")
#
#    def grasp_cb(self, msg):
#        self.latest_grasp = msg
#
#    def drop_cb(self, msg):
#        self.latest_drop = msg
#
#    def stop_base(self):
#        self.cmd_vel_pub.publish(Twist())
#        rospy.sleep(0.5)
#
#    def drive_for_time(self, linear_x, duration):
#        cmd = Twist()
#        cmd.linear.x = linear_x
#        rate = rospy.Rate(10)
#        start = rospy.Time.now()
#
#        while (rospy.Time.now() - start).to_sec() < duration and not rospy.is_shutdown():
#            self.cmd_vel_pub.publish(cmd)
#            rate.sleep()
#
#        self.stop_base()
#
#    def turn_for_time(self, angular_z, duration):
#        cmd = Twist()
#        cmd.angular.z = angular_z
#        rate = rospy.Rate(10)
#        start = rospy.Time.now()
#
#        while (rospy.Time.now() - start).to_sec() < duration and not rospy.is_shutdown():
#            self.cmd_vel_pub.publish(cmd)
#            rate.sleep()
#
#        self.stop_base()
#
#    def turn_left_90(self):
#        rospy.loginfo("Turning left 90 degrees...")
#        self.turn_for_time(abs(self.turn_speed), self.turn_90_duration)
#
#    def turn_right_90(self):
#        rospy.loginfo("Turning right 90 degrees...")
#        self.turn_for_time(-abs(self.turn_speed), self.turn_90_duration)
#
#    def drive_forward_distance(self, distance):
#        if abs(distance) < 1e-4:
#            return
#
#        duration = abs(distance) / self.drive_speed
#        speed = self.drive_speed if distance > 0 else -self.drive_speed
#
#        rospy.loginfo("Driving %.3f m", distance)
#        self.drive_for_time(speed, duration)
#
#    def wait_for_target(self, target_type):
#        rospy.loginfo("Waiting for %s target...", target_type)
#        rate = rospy.Rate(10)
#
#        while not rospy.is_shutdown():
#            target = self.latest_grasp if target_type == "grasp" else self.latest_drop
#
#            if target is not None:
#                rospy.loginfo(
#                    "Got %s target: x=%.3f, y=%.3f, z=%.3f",
#                    target_type, target.point.x, target.point.y, target.point.z
#                )
#                return target
#            rate.sleep()
#        return None
#
#    def lateral_move_to_target_y(self, target):
#        desired_y = 0.00
#        y = target.point.y - desired_y
#
#        rospy.loginfo("Lateral correction: current y=%.3f, desired y=%.3f, moving %.3f", target.point.y, desired_y, y)
#        if abs(y) < 0.05:
#            rospy.loginfo("Target already close to y=0. No lateral move needed.")
#            return
#
#        if y > 0.0:
#            self.turn_left_90()
#            self.drive_forward_distance(abs(y))
#            self.turn_right_90()
#        else:
#            self.turn_right_90()
#            self.drive_forward_distance(abs(y))
#            self.turn_left_90()
#
#        rospy.sleep(2.0)
#
#    def move_from_box_a_to_box_b(self):
#        rospy.loginfo("Moving from Box A to Box B...")
#        self.turn_right_90()
#        self.drive_forward_distance(self.box_distance)
#        rospy.loginfo("Turning left 90 degrees...")
#        self.turn_for_time(abs(self.turn_speed), self.turn_90_duration)
#        rospy.sleep(2.0)
#
#    def run(self):
#        rospy.sleep(2.0)
#
#        # 1. Wait for the vision node to find Box A
#        initial_grasp = self.wait_for_target("grasp")
#        if initial_grasp is None:
#            return
#
#        # 2. Align the base to face Box A head-on
#        self.lateral_move_to_target_y(initial_grasp)
#        self.drive_forward_distance(-0.10)
#        
#        rospy.loginfo("--- ALIGNMENT COMPLETE ---")
#        
#        # 3. Pause Execution. Wait for user input in the terminal.
#        # This gives you all the time you need to check Rviz and your PCL output.
#        try:
#            input("\n>>> Robot is aligned with Box A. Check your vision pipeline now.\n>>> Press ENTER to move to Box B...\n")
#        except EOFError:
#            pass # Handles Ctrl+D gracefully
#
#        # 4. Move to Box B
#        self.move_from_box_a_to_box_b()
#        self.drive_forward_distance(0.20)
#
#        rospy.loginfo("--- ARRIVED AT BOX B ---")
#        
#        try:
#            input("\n>>> Robot is aligned with Box B. Check your vision pipeline now.\n>>> Press ENTER to exit...\n")
#        except EOFError:
#            pass
#
#        rospy.loginfo("Test complete.")
#
#if __name__ == "__main__":
#    try:
#        node = VisionTestDriver()
#        node.run()
#    except rospy.ROSInterruptException:
#        pass
#
#


#!/usr/bin/env python3

import sys
import rospy
import moveit_commander
from moveit_commander import conversions
import sensor_msgs.point_cloud2 as pc2

from geometry_msgs.msg import PointStamped, PoseStamped, Twist
from moveit_msgs.msg import RobotTrajectory
from sensor_msgs.msg import PointCloud2
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint


class LaundryManipulationNode:
    def __init__(self):
        rospy.init_node("laundry_manipulation_node")

        self.latest_grasp = None
        self.latest_drop = None
        self.latest_table_cloud = None
        self.latest_box_a_target = None
        self.latest_box_b_target = None
        self.latest_box_a_cloud = None
        self.latest_box_b_cloud = None
        self.latest_box_a_floor_cloud = None
        self.latest_box_b_floor_cloud = None
        self.executing = False
        self.box_a_floor_z = None
        self.box_b_floor_z = None

        self.drive_speed = rospy.get_param("~drive_speed", 0.05)
        self.turn_speed = rospy.get_param("~turn_speed", 0.10)
        self.turn_90_duration = rospy.get_param("~turn_90_duration", 15.70)
        self.box_distance = rospy.get_param("~box_distance", 0.50)
        self.target_frame = rospy.get_param("~target_frame", "base_footprint")
        self.grasp_height_above_floor = rospy.get_param("~grasp_height_above_floor", 0.02)
        self.gripper_tip_offset = rospy.get_param("~gripper_tip_offset", 0.10)
        self.box_a_length = rospy.get_param("~box_a_length", 0.30)
        self.box_a_width = rospy.get_param("~box_a_width", 0.30)
        self.box_a_height = rospy.get_param("~box_a_height", 0.38)
        self.box_b_length = rospy.get_param("~box_b_length", 0.40)
        self.box_b_width = rospy.get_param("~box_b_width", 0.30)
        self.box_b_height = rospy.get_param("~box_b_height", 0.21)
        self.box_wall_thickness = rospy.get_param("~box_wall_thickness", 0.03)
        self.box_floor_thickness = rospy.get_param("~box_floor_thickness", 0.01)
        self.box_safety_margin = rospy.get_param("~box_safety_margin", 0.02)
        self.grasp_z_offset = rospy.get_param("~grasp_z_offset", 0.0)

        rospy.Subscriber("/tiago_vision/clothes_grasp_target", PointStamped, self.grasp_cb)
        rospy.Subscriber("/tiago_vision/clothes_drop_target", PointStamped, self.drop_cb)
        rospy.Subscriber("/tiago_vision/box_a_target", PointStamped, self.box_a_target_cb)
        rospy.Subscriber("/tiago_vision/box_b_target", PointStamped, self.box_b_target_cb)
        rospy.Subscriber("/tiago_vision/box_a_cloud", PointCloud2, self.box_a_cloud_cb)
        rospy.Subscriber("/tiago_vision/box_b_cloud", PointCloud2, self.box_b_cloud_cb)

        self.cmd_vel_pub = rospy.Publisher("/mobile_base_controller/cmd_vel", Twist, queue_size=1)
        self.gripper_pub = rospy.Publisher("/gripper_controller/command", JointTrajectory, queue_size=1)

        moveit_commander.roscpp_initialize(sys.argv)
        self.scene = moveit_commander.PlanningSceneInterface()
        self.arm = moveit_commander.MoveGroupCommander("arm_torso", wait_for_servers=10.0)
        self.arm.set_planning_time(20.0)
        self.arm.set_num_planning_attempts(10)
        self.arm.set_max_velocity_scaling_factor(0.3)
        self.arm.set_max_acceleration_scaling_factor(0.3)
        self.arm.set_goal_position_tolerance(0.03)
        self.arm.set_goal_orientation_tolerance(0.30)

        rospy.loginfo("Laundry manipulation node initialized.")

    def grasp_cb(self, msg):
        if not self.executing:
            self.latest_grasp = msg

    def drop_cb(self, msg):
        if not self.executing:
            self.latest_drop = msg

    def box_a_target_cb(self, msg):
        if not self.executing:
            self.latest_box_a_target = msg

    def box_b_target_cb(self, msg):
        if not self.executing:
            self.latest_box_b_target = msg

    def table_cloud_cb(self, msg):
        if not self.executing:
            self.latest_table_cloud = msg

    def box_a_cloud_cb(self, msg):
        if not self.executing:
            self.latest_box_a_cloud = msg

    def box_b_cloud_cb(self, msg):
        if not self.executing:
            self.latest_box_b_cloud = msg

    def box_a_floor_cloud_cb(self, msg):
        if not self.executing:
            self.latest_box_a_floor_cloud = msg

    def box_b_floor_cloud_cb(self, msg):
        if not self.executing:
            self.latest_box_b_floor_cloud = msg

    def clear_latest_clouds(self):
        self.latest_table_cloud = None
        self.latest_box_a_target = None
        self.latest_box_b_target = None
        self.latest_box_a_cloud = None
        self.latest_box_b_cloud = None
        self.latest_box_a_floor_cloud = None
        self.latest_box_b_floor_cloud = None

    def stop_base(self):
        self.cmd_vel_pub.publish(Twist())
        rospy.sleep(0.5)

    def drive_for_time(self, linear_x, duration):
        cmd = Twist()
        cmd.linear.x = linear_x
        rate = rospy.Rate(10)
        start = rospy.Time.now()

        while (rospy.Time.now() - start).to_sec() < duration and not rospy.is_shutdown():
            self.cmd_vel_pub.publish(cmd)
            rate.sleep()

        self.stop_base()

    def turn_for_time(self, angular_z, duration):
        cmd = Twist()
        cmd.angular.z = angular_z
        rate = rospy.Rate(10)
        start = rospy.Time.now()

        while (rospy.Time.now() - start).to_sec() < duration and not rospy.is_shutdown():
            self.cmd_vel_pub.publish(cmd)
            rate.sleep()

        self.stop_base()

    def turn_left_90(self):
        rospy.loginfo("Turning left 90 degrees...")
        self.turn_for_time(abs(self.turn_speed), self.turn_90_duration)

    def turn_right_90(self):
        rospy.loginfo("Turning right 90 degrees...")
        self.turn_for_time(-abs(self.turn_speed), self.turn_90_duration)

    def drive_forward_distance(self, distance):

        if abs(distance) < 1e-4:
            return

        duration = abs(distance) / self.drive_speed

        speed = self.drive_speed if distance > 0 else -self.drive_speed

        rospy.loginfo(
            "Driving %.3f m", distance
        )

        self.drive_for_time(speed, duration)
    def wait_for_target(self, target_type):
        rospy.loginfo("Waiting for %s target...", target_type)
        rate = rospy.Rate(10)

        while not rospy.is_shutdown():
            target = self.latest_grasp if target_type == "grasp" else self.latest_drop

            if target is not None:
                rospy.loginfo(
                    "Got %s target: x=%.3f, y=%.3f, z=%.3f",
                    target_type,
                    target.point.x,
                    target.point.y,
                    target.point.z
                )
                return target

            rate.sleep()

        return None

    def wait_for_fresh_target(self, target_type, after_time):
        rospy.loginfo("Waiting for fresh %s target...", target_type)
        rate = rospy.Rate(10)

        while not rospy.is_shutdown():
            target = self.latest_grasp if target_type == "grasp" else self.latest_drop

            if target is not None:
                if target.header.stamp >= after_time:
                    rospy.loginfo(
                        "Got fresh %s target: x=%.3f, y=%.3f, z=%.3f",
                        target_type,
                        target.point.x,
                        target.point.y,
                        target.point.z
                    )
                    return target

            rate.sleep()

        return None

    def wait_for_box_target(self, box_name, timeout=10.0):
        rospy.loginfo("Waiting for %s target...", box_name)
        start = rospy.Time.now()
        rate = rospy.Rate(10)

        while (rospy.Time.now() - start).to_sec() < timeout and not rospy.is_shutdown():
            target = self.latest_box_a_target if box_name == "box_a" else self.latest_box_b_target

            if target is not None:
                rospy.loginfo(
                    "Got %s target: x=%.3f, y=%.3f, z=%.3f",
                    box_name,
                    target.point.x,
                    target.point.y,
                    target.point.z,
                )
                return target

            rate.sleep()

        rospy.logwarn("Timed out waiting for %s target.", box_name)
        return None

    def wait_for_cloud(self, cloud_name, timeout=3.0, after_time=None):
        start = rospy.Time.now()
        rate = rospy.Rate(10)

        while (rospy.Time.now() - start).to_sec() < timeout and not rospy.is_shutdown():
            cloud = getattr(self, cloud_name)
            if cloud is not None:
                if after_time is None or cloud.header.stamp >= after_time:
                    return cloud
            rate.sleep()

        rospy.logwarn("Timed out waiting for %s.", cloud_name)
        return None

    def point_cloud_bounds(self, cloud_msg):
        points = pc2.read_points(cloud_msg, field_names=("x", "y", "z"), skip_nans=True)
        min_x = min_y = min_z = float("inf")
        max_x = max_y = max_z = float("-inf")
        count = 0

        for x, y, z in points:
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            min_z = min(min_z, z)
            max_x = max(max_x, x)
            max_y = max(max_y, y)
            max_z = max(max_z, z)
            count += 1

        if count == 0:
            return None

        return {
            "frame_id": cloud_msg.header.frame_id or self.target_frame,
            "min_x": min_x,
            "max_x": max_x,
            "min_y": min_y,
            "max_y": max_y,
            "min_z": min_z,
            "max_z": max_z,
        }

    def add_collision_box(self, name, frame_id, center, size):
        pose = PoseStamped()
        pose.header.frame_id = frame_id
        pose.header.stamp = rospy.Time.now()
        pose.pose.position.x = center[0]
        pose.pose.position.y = center[1]
        pose.pose.position.z = center[2]
        pose.pose.orientation.w = 1.0

        self.scene.add_box(name, pose, size=size)
        rospy.loginfo(
            "Added collision box %s center=(%.3f, %.3f, %.3f) size=(%.3f, %.3f, %.3f)",
            name,
            center[0], center[1], center[2],
            size[0], size[1], size[2]
        )

    def clear_collision_scene(self):
        for name in [
            "table",
            "box_a_floor",
            "box_a_left_wall",
            "box_a_right_wall",
            "box_a_back_wall",
            "box_a_top_wall",
            "box_b_floor",
            "box_b_left_wall",
            "box_b_right_wall",
            "box_b_front_wall",
            "box_b_back_wall",
        ]:
            self.scene.remove_world_object(name)
        rospy.sleep(0.5)

    def add_fixed_box_a_collisions(self, box_target):
        if box_target is None:
            rospy.logwarn("Cannot add Box A collision: missing /tiago_vision/box_a_target.")
            return False

        frame_id = box_target.header.frame_id or self.target_frame
        center_x = box_target.point.x
        center_y = box_target.point.y
        center_z = box_target.point.z

        length = self.box_a_length
        width = self.box_a_width
        height = self.box_a_height
        margin = self.box_safety_margin
        wall = self.box_wall_thickness
        floor = self.box_floor_thickness

        min_x = center_x - 0.5 * length - margin
        max_x = center_x + 0.5 * length + margin
        min_y = center_y - 0.5 * width - margin
        max_y = center_y + 0.5 * width + margin
        floor_z = center_z - 0.5 * height
        wall_center_z = floor_z + 0.5 * height

        self.box_a_floor_z = floor_z

        usable_length = max(max_x - min_x, 0.10)
        usable_width = max(max_y - min_y, 0.10)

        self.add_collision_box(
            "box_a_floor",
            frame_id,
            (center_x, center_y, floor_z - 0.5 * floor),
            (usable_length, usable_width, floor),
        )
        self.add_collision_box(
            "box_a_left_wall",
            frame_id,
            (center_x, max_y + 0.5 * wall, wall_center_z),
            (usable_length, wall, height),
        )
        self.add_collision_box(
            "box_a_right_wall",
            frame_id,
            (center_x, min_y - 0.5 * wall, wall_center_z),
            (usable_length, wall, height),
        )
        self.add_collision_box(
            "box_a_back_wall",
            frame_id,
            (max_x + 0.5 * wall, center_y, wall_center_z),
            (wall, usable_width, height),
        )
        rospy.loginfo(
            "Box A fixed collision from YOLO target: center=(%.3f, %.3f, %.3f), size=(%.2f, %.2f, %.2f)",
            center_x,
            center_y,
            center_z,
            length,
            width,
            height,
        )
        return True

    def add_fixed_box_b_collisions(self, box_target):
        if box_target is None:
            rospy.logwarn("Cannot add Box B collision: missing /tiago_vision/box_b_target.")
            return False

        frame_id = box_target.header.frame_id or self.target_frame
        center_x = box_target.point.x
        center_y = box_target.point.y
        center_z = box_target.point.z

        length = self.box_b_length
        width = self.box_b_width
        height = self.box_b_height
        margin = self.box_safety_margin
        wall = self.box_wall_thickness
        floor = self.box_floor_thickness

        min_x = center_x - 0.5 * length - margin
        max_x = center_x + 0.5 * length + margin
        min_y = center_y - 0.5 * width - margin
        max_y = center_y + 0.5 * width + margin
        floor_z = center_z - 0.5 * height
        wall_center_z = floor_z + 0.5 * height

        self.box_b_floor_z = floor_z

        usable_length = max(max_x - min_x, 0.10)
        usable_width = max(max_y - min_y, 0.10)

        self.add_collision_box(
            "box_b_floor",
            frame_id,
            (center_x, center_y, floor_z - 0.5 * floor),
            (usable_length, usable_width, floor),
        )
        self.add_collision_box(
            "box_b_left_wall",
            frame_id,
            (center_x, max_y + 0.5 * wall, wall_center_z),
            (usable_length, wall, height),
        )
        self.add_collision_box(
            "box_b_right_wall",
            frame_id,
            (center_x, min_y - 0.5 * wall, wall_center_z),
            (usable_length, wall, height),
        )
        self.add_collision_box(
            "box_b_back_wall",
            frame_id,
            (max_x + 0.5 * wall, center_y, wall_center_z),
            (wall, usable_width, height),
        )
        self.add_collision_box(
            "box_b_front_wall",
            frame_id,
            (min_x - 0.5 * wall, center_y, wall_center_z),
            (wall, usable_width, height),
        )

        rospy.loginfo(
            "Box B fixed collision from YOLO target: center=(%.3f, %.3f, %.3f), size=(%.2f, %.2f, %.2f)",
            center_x,
            center_y,
            center_z,
            length,
            width,
            height,
        )
        return True

    def add_table_collision(self, table_cloud):
        bounds = self.point_cloud_bounds(table_cloud)
        if bounds is None:
            rospy.logwarn("Cannot add table collision: empty table cloud.")
            return False

        thickness = 0.08
        table_margin_xy = 0.05
        table_top_margin = 0.0
        table_top_z = bounds["max_z"] + table_top_margin
        center = (
            0.5 * (bounds["min_x"] + bounds["max_x"]),
            0.5 * (bounds["min_y"] + bounds["max_y"]),
            table_top_z - 0.5 * thickness,
        )
        size = (
            max(bounds["max_x"] - bounds["min_x"] + 2.0 * table_margin_xy, 0.10),
            max(bounds["max_y"] - bounds["min_y"] + 2.0 * table_margin_xy, 0.10),
            thickness,
        )
        self.add_collision_box("table", bounds["frame_id"], center, size)
        return True

    def add_box_wall_collisions(self, prefix, box_cloud, floor_cloud, include_front_wall, include_top_wall=False):
        if box_cloud is None or floor_cloud is None:
            rospy.logwarn("Cannot add %s collision: missing box or floor cloud.", prefix)
            return False

        box_bounds = self.point_cloud_bounds(box_cloud)
        floor_bounds = self.point_cloud_bounds(floor_cloud)

        if box_bounds is None or floor_bounds is None:
            rospy.logwarn("Cannot add %s collision: missing box or floor cloud.", prefix)
            return False

        frame_id = box_bounds["frame_id"]
        box_margin_xy = 0.06
        wall_thickness = 0.05
        floor_thickness = 0.01
        top_wall_thickness = 0.05
        wall_height_margin = 0.05
        min_x = box_bounds["min_x"] - box_margin_xy
        max_x = box_bounds["max_x"] + box_margin_xy
        min_y = box_bounds["min_y"] - box_margin_xy
        max_y = box_bounds["max_y"] + box_margin_xy
        floor_z = floor_bounds["min_z"]
        if prefix == "box_a":
            self.box_a_floor_z = floor_z
        elif prefix == "box_b":
            self.box_b_floor_z = floor_z

        wall_height = max(box_bounds["max_z"] - floor_z + wall_height_margin, 0.25)
        wall_center_z = floor_z + 0.5 * wall_height

        width_x = max(max_x - min_x, 0.10)
        width_y = max(max_y - min_y, 0.10)

        self.add_collision_box(
            prefix + "_floor",
            frame_id,
            (0.5 * (min_x + max_x), 0.5 * (min_y + max_y), floor_z - 0.5 * floor_thickness),
            (width_x, width_y, floor_thickness),
        )
        self.add_collision_box(
            prefix + "_left_wall",
            frame_id,
            (0.5 * (min_x + max_x), max_y + 0.5 * wall_thickness, wall_center_z),
            (width_x, wall_thickness, wall_height),
        )
        self.add_collision_box(
            prefix + "_right_wall",
            frame_id,
            (0.5 * (min_x + max_x), min_y - 0.5 * wall_thickness, wall_center_z),
            (width_x, wall_thickness, wall_height),
        )
        self.add_collision_box(
            prefix + "_back_wall",
            frame_id,
            (max_x + 0.5 * wall_thickness, 0.5 * (min_y + max_y), wall_center_z),
            (wall_thickness, width_y, wall_height),
        )

        if include_top_wall:
            self.add_collision_box(
                prefix + "_top_wall",
                frame_id,
                (0.5 * (min_x + max_x), 0.5 * (min_y + max_y), box_bounds["max_z"]),
                (width_x, width_y, top_wall_thickness),
            )

        if include_front_wall:
            self.add_collision_box(
                prefix + "_front_wall",
                frame_id,
                (min_x - 0.5 * wall_thickness, 0.5 * (min_y + max_y), wall_center_z),
                (wall_thickness, width_y, wall_height),
            )

        return True

    def setup_collision_scene(self, phase, after_time=None):
        rospy.loginfo("Setting up %s collision scene...", phase)
        self.clear_collision_scene()

        if phase == "pick":
            box_target = self.wait_for_box_target("box_a")
            ok = self.add_fixed_box_a_collisions(box_target)
        else:
            box_target = self.wait_for_box_target("box_b")
            if box_target is None and self.latest_drop is not None:
                box_target = self.latest_drop
                rospy.logwarn(
                    "Using /tiago_vision/clothes_drop_target as Box B collision center."
                )
            ok = self.add_fixed_box_b_collisions(box_target)

        rospy.sleep(1.0)
        return ok

    def lateral_move_to_target_y(self, target):
        desired_y = 0.15
        y = target.point.y - desired_y

        rospy.loginfo(
            "Lateral correction: current y=%.3f, desired y=%.3f, moving %.3f",
            target.point.y,
            desired_y,
            y
        )
        if abs(y) < 0.05:
            rospy.loginfo("Target already close to y=0. No lateral move needed.")
            return

        if y > 0.0:
            self.turn_left_90()
            self.drive_forward_distance(abs(y))
            self.turn_right_90()
        else:
            self.turn_right_90()
            self.drive_forward_distance(abs(y))
            self.turn_left_90()

        rospy.sleep(2.0)

    def move_from_box_a_to_box_b(self):
        rospy.loginfo("Turning right 30 degrees after grasp...")
        self.turn_for_time(
            -abs(self.turn_speed),
            self.turn_90_duration * 30.0 / 90.0
        )
        self.drive_forward_distance(0.35)

        rospy.sleep(2.0)

    def make_pose(self, point_msg, x_offset=0.0, y_offset=0.0, z_offset=0.0, absolute_z=None):
        pose = PoseStamped()

        # Force current time and base_footprint to avoid old TF timestamp problems.
        pose.header.frame_id = self.target_frame
        pose.header.stamp = rospy.Time.now()

        if absolute_z is None:
            # Do not fully trust the detected z value. Sometimes the point cloud detects
            # the box edge or the upper surface instead of the cloth center.
            safe_z = max(min(point_msg.point.z, 0.55), 0.40)
        else:
            safe_z = absolute_z

        pose.pose.position.x = point_msg.point.x + x_offset
        pose.pose.position.y = point_msg.point.y + y_offset
        pose.pose.position.z = safe_z + z_offset

        # Keep the same simple orientation, but the orientation tolerance above is relaxed.
        pose.pose.orientation.x = 0.0
        pose.pose.orientation.y = 0.0
        pose.pose.orientation.z = 0.0
        pose.pose.orientation.w = 1.0

        return pose

    def move_to_pose(self, pose, label):
        rospy.loginfo("Moving to %s...", label)

        self.arm.set_pose_target(pose)
        success = self.arm.go(wait=True)

        self.arm.stop()
        self.arm.clear_pose_targets()

        if success:
            rospy.loginfo("Reached %s.", label)
        else:
            rospy.logwarn("Failed to reach %s.", label)

        return success

    def move_cartesian_to_pose(self, pose, label, eef_step=0.005, min_fraction=0.90):
        rospy.loginfo("Moving to %s with Cartesian path...", label)

        waypoints = [conversions.pose_to_list(pose.pose)]
        ser_path, fraction = self.arm._g.compute_cartesian_path(
            waypoints,
            eef_step,
            0.0,
            True,
        )
        plan = RobotTrajectory()
        plan.deserialize(ser_path)

        rospy.loginfo(
            "Cartesian path to %s fraction: %.3f",
            label,
            fraction,
        )

        if fraction < min_fraction:
            rospy.logwarn(
                "Cartesian path to %s incomplete: fraction %.3f < %.3f",
                label,
                fraction,
                min_fraction,
            )
            return False

        success = self.arm.execute(plan, wait=True)
        self.arm.stop()
        self.arm.clear_pose_targets()

        if success:
            rospy.loginfo("Reached %s with Cartesian path.", label)
        else:
            rospy.logwarn("Failed to execute Cartesian path to %s.", label)

        return success

    def send_gripper_command(self, finger_position):
        traj = JointTrajectory()
        traj.joint_names = [
            "gripper_left_finger_joint",
            "gripper_right_finger_joint"
        ]

        point = JointTrajectoryPoint()
        point.positions = [finger_position, finger_position]
        point.velocities = [0.0, 0.0]
        point.time_from_start = rospy.Duration(1.0)

        traj.points.append(point)
        self.gripper_pub.publish(traj)

    def open_gripper(self):
        rospy.loginfo("Opening gripper...")
        self.send_gripper_command(0.045)
        rospy.sleep(1.5)

    def close_gripper(self):
        rospy.loginfo("Closing gripper...")
        self.send_gripper_command(0.0)
        rospy.sleep(1.5)

    def move_arm_to_carry_pose(self):
        rospy.loginfo("Moving arm to carry pose...")

        joint_goal = {
            "torso_lift_joint": 0.15,
            "arm_1_joint": 0.20,
            "arm_2_joint": -1.30,
            "arm_3_joint": -0.20,
            "arm_4_joint": 1.90,
            "arm_5_joint": -1.57,
            "arm_6_joint": 1.30,
            "arm_7_joint": 0.00,
        }

        self.arm.set_joint_value_target(joint_goal)
        success = self.arm.go(wait=True)
        self.arm.stop()

        if success:
            rospy.loginfo("Reached carry pose.")
        else:
            rospy.logwarn("Failed to reach carry pose.")

        return success

    def pick_cloth(self, grasp_target):
        rospy.loginfo(
            "Raw grasp target: x=%.3f, y=%.3f, z=%.3f",
            grasp_target.point.x,
            grasp_target.point.y,
            grasp_target.point.z
        )

        grasp_z = grasp_target.point.z + self.grasp_z_offset

        pre_grasp_z = grasp_z + 0.08
        lift_z = grasp_z + 0.18

        # The gripper fingers extend forward from the controlled end-effector pose.
        # Keep the commanded pose behind the target so the fingertips, not the wrist,
        # approach the cloth.
        pre_grasp_x_offset = -(self.gripper_tip_offset + 0.17)
        grasp_x_offset = pre_grasp_x_offset + 0.06
        lift_x_offset = -(self.gripper_tip_offset + 0.18)

        pre_grasp = self.make_pose(
            grasp_target,
            x_offset=pre_grasp_x_offset,
            absolute_z=pre_grasp_z,
        )
        grasp = self.make_pose(
            grasp_target,
            x_offset=grasp_x_offset,
            absolute_z=grasp_z,
        )
        lift = self.make_pose(
            grasp_target,
            x_offset=lift_x_offset,
            absolute_z=lift_z,
        )

        rospy.loginfo(
            "Safe pre-grasp: x=%.3f, y=%.3f, z=%.3f",
            pre_grasp.pose.position.x,
            pre_grasp.pose.position.y,
            pre_grasp.pose.position.z
        )
        rospy.loginfo(
            "Safe grasp: x=%.3f, y=%.3f, z=%.3f",
            grasp.pose.position.x,
            grasp.pose.position.y,
            grasp.pose.position.z
        )

        self.open_gripper()

        if not self.move_to_pose(pre_grasp, "pre-grasp pose"):
            return False

        if not self.move_cartesian_to_pose(grasp, "grasp pose"):
            return False

        self.close_gripper()

        if not self.move_to_pose(lift, "lift pose"):
            return False

        self.move_arm_to_carry_pose()
        return True

    def place_cloth(self, drop_target):
        pre_drop = self.make_pose(drop_target, z_offset=0.46)
        drop = self.make_pose(drop_target, z_offset=0.36)

        rospy.loginfo(
            "Safe drop target: x=%.3f, y=%.3f, z=%.3f",
            drop.pose.position.x,
            drop.pose.position.y,
            drop.pose.position.z
        )

        if not self.move_to_pose(pre_drop, "pre-drop pose"):
            return False

        if not self.move_to_pose(drop, "drop pose"):
            return False

        self.open_gripper()

        if not self.move_to_pose(pre_drop, "retreat pose"):
            return False

        self.move_arm_to_carry_pose()
        return True

    def run(self):
        rospy.sleep(2.0)

        rospy.loginfo("YOLO pick-and-place mode with slow open-loop base motion.")

        grasp_target = self.wait_for_target("grasp")
        if grasp_target is None:
            return

        if not self.setup_collision_scene("pick"):
            rospy.logwarn("Pick collision scene setup failed.")
            return

        self.executing = True

        if not self.pick_cloth(grasp_target):
            rospy.logwarn("Pick cloth failed.")
            self.executing = False
            return

        self.executing = False

        rospy.sleep(1.0)

        self.latest_grasp = None
        self.latest_drop = None
        self.latest_box_b_target = None
        self.clear_latest_clouds()

        self.move_from_box_a_to_box_b()

        rospy.sleep(2.0)

        drop_target = self.wait_for_target("drop")
        if drop_target is None:
            return

        if not self.setup_collision_scene("place"):
            rospy.logwarn("Place collision scene setup failed.")
            return

        self.executing = True

        if not self.place_cloth(drop_target):
            rospy.logwarn("Place cloth failed.")
            self.executing = False
            return

        self.executing = False
        self.stop_base()

        rospy.loginfo("YOLO pick-and-place task completed.")
        rospy.spin()


if __name__ == "__main__":
    try:
        node = LaundryManipulationNode()
        node.run()
    except rospy.ROSInterruptException:
        pass
