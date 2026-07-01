# #!/usr/bin/env python3

# import sys
# import rospy
# import moveit_commander

# from geometry_msgs.msg import PointStamped, PoseStamped, Twist
# from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint


# class LaundryManipulationNode:
#     def __init__(self):
#         rospy.init_node("laundry_manipulation_node")

#         self.latest_grasp = None
#         self.latest_drop = None
#         self.executing = False

#         self.drive_speed = rospy.get_param("~drive_speed", 0.05)
#         self.turn_speed = rospy.get_param("~turn_speed", 0.25)
#         self.turn_90_duration = rospy.get_param("~turn_90_duration", 6.28)
#         self.box_distance = rospy.get_param("~box_distance", 0.72)
#         self.target_frame = rospy.get_param("~target_frame", "base_footprint")

#         rospy.Subscriber("/tiago_vision/clothes_grasp_target", PointStamped, self.grasp_cb)
#         rospy.Subscriber("/tiago_vision/clothes_drop_target", PointStamped, self.drop_cb)

#         self.cmd_vel_pub = rospy.Publisher("/mobile_base_controller/cmd_vel", Twist, queue_size=1)
#         self.gripper_pub = rospy.Publisher("/gripper_controller/command", JointTrajectory, queue_size=1)

#         moveit_commander.roscpp_initialize(sys.argv)
#         self.arm = moveit_commander.MoveGroupCommander("arm_torso")
#         self.arm.set_planning_time(20.0)
#         self.arm.set_num_planning_attempts(10)
#         self.arm.set_max_velocity_scaling_factor(0.3)
#         self.arm.set_max_acceleration_scaling_factor(0.3)
#         self.arm.set_goal_position_tolerance(0.03)
#         self.arm.set_goal_orientation_tolerance(0.30)

#         rospy.loginfo("Laundry manipulation node initialized.")

#     def grasp_cb(self, msg):
#         if not self.executing:
#             self.latest_grasp = msg

#     def drop_cb(self, msg):
#         if not self.executing:
#             self.latest_drop = msg

#     def stop_base(self):
#         self.cmd_vel_pub.publish(Twist())
#         rospy.sleep(0.5)

#     def drive_for_time(self, linear_x, duration):
#         cmd = Twist()
#         cmd.linear.x = linear_x
#         rate = rospy.Rate(10)
#         start = rospy.Time.now()

#         while (rospy.Time.now() - start).to_sec() < duration and not rospy.is_shutdown():
#             self.cmd_vel_pub.publish(cmd)
#             rate.sleep()

#         self.stop_base()

#     def turn_for_time(self, angular_z, duration):
#         cmd = Twist()
#         cmd.angular.z = angular_z
#         rate = rospy.Rate(10)
#         start = rospy.Time.now()

#         while (rospy.Time.now() - start).to_sec() < duration and not rospy.is_shutdown():
#             self.cmd_vel_pub.publish(cmd)
#             rate.sleep()

#         self.stop_base()

#     def turn_left_90(self):
#         rospy.loginfo("Turning left 90 degrees...")
#         self.turn_for_time(abs(self.turn_speed), self.turn_90_duration)

#     def turn_right_90(self):
#         rospy.loginfo("Turning right 90 degrees...")
#         self.turn_for_time(-abs(self.turn_speed), self.turn_90_duration)

#     def drive_forward_distance(self, distance):

#         if abs(distance) < 1e-4:
#             return

#         duration = abs(distance) / self.drive_speed

#         speed = self.drive_speed if distance > 0 else -self.drive_speed

#         rospy.loginfo(
#             "Driving %.3f m", distance
#         )

#         self.drive_for_time(speed, duration)
#     def wait_for_target(self, target_type):
#         rospy.loginfo("Waiting for %s target...", target_type)
#         rate = rospy.Rate(10)

#         while not rospy.is_shutdown():
#             target = self.latest_grasp if target_type == "grasp" else self.latest_drop

#             if target is not None:
#                 rospy.loginfo(
#                     "Got %s target: x=%.3f, y=%.3f, z=%.3f",
#                     target_type,
#                     target.point.x,
#                     target.point.y,
#                     target.point.z
#                 )
#                 return target

#             rate.sleep()

#         return None

#     def wait_for_fresh_target(self, target_type, after_time):
#         rospy.loginfo("Waiting for fresh %s target...", target_type)
#         rate = rospy.Rate(10)

#         while not rospy.is_shutdown():
#             target = self.latest_grasp if target_type == "grasp" else self.latest_drop

#             if target is not None:
#                 if target.header.stamp >= after_time:
#                     rospy.loginfo(
#                         "Got fresh %s target: x=%.3f, y=%.3f, z=%.3f",
#                         target_type,
#                         target.point.x,
#                         target.point.y,
#                         target.point.z
#                     )
#                     return target

#             rate.sleep()

#         return None

#     def lateral_move_to_target_y(self, target):
#         desired_y = 0.15
#         y = target.point.y - desired_y

#         rospy.loginfo(
#             "Lateral correction: current y=%.3f, desired y=%.3f, moving %.3f",
#             target.point.y,
#             desired_y,
#             y
#         )
#         if abs(y) < 0.05:
#             rospy.loginfo("Target already close to y=0. No lateral move needed.")
#             return

#         if y > 0.0:
#             self.turn_left_90()
#             self.drive_forward_distance(abs(y))
#             self.turn_right_90()
#         else:
#             self.turn_right_90()
#             self.drive_forward_distance(abs(y))
#             self.turn_left_90()

#         rospy.sleep(2.0)

#     def move_from_box_a_to_box_b(self):
#         rospy.loginfo("Moving from Box A to Box B...")

#         self.turn_right_90()
#         self.drive_forward_distance(self.box_distance - 0.15)
#         # self.turn_left_90()
#         rospy.loginfo("Turning left 90 degrees...")
#         self.turn_for_time(
#             abs(self.turn_speed),
#             self.turn_90_duration * 90.0 / 90.0
#         )

#         rospy.sleep(2.0)

#     def make_pose(self, point_msg, x_offset=0.0, y_offset=0.0, z_offset=0.0):
#         pose = PoseStamped()

#         # Force current time and base_footprint to avoid old TF timestamp problems.
#         pose.header.frame_id = self.target_frame
#         pose.header.stamp = rospy.Time.now()

#         # Do not fully trust the detected z value. Sometimes the point cloud detects
#         # the box edge or the upper surface instead of the cloth center.
#         safe_z = max(min(point_msg.point.z, 0.55), 0.40)

#         pose.pose.position.x = point_msg.point.x + x_offset
#         pose.pose.position.y = point_msg.point.y + y_offset
#         pose.pose.position.z = safe_z + z_offset

#         # Keep the same simple orientation, but the orientation tolerance above is relaxed.
#         pose.pose.orientation.x = 0.0
#         pose.pose.orientation.y = 0.0
#         pose.pose.orientation.z = 0.0
#         pose.pose.orientation.w = 1.0

#         return pose

#     def move_to_pose(self, pose, label):
#         rospy.loginfo("Moving to %s...", label)

#         self.arm.set_pose_target(pose)
#         success = self.arm.go(wait=True)

#         self.arm.stop()
#         self.arm.clear_pose_targets()

#         if success:
#             rospy.loginfo("Reached %s.", label)
#         else:
#             rospy.logwarn("Failed to reach %s.", label)

#         return success

#     def send_gripper_command(self, finger_position):
#         traj = JointTrajectory()
#         traj.joint_names = [
#             "gripper_left_finger_joint",
#             "gripper_right_finger_joint"
#         ]

#         point = JointTrajectoryPoint()
#         point.positions = [finger_position, finger_position]
#         point.velocities = [0.0, 0.0]
#         point.time_from_start = rospy.Duration(1.0)

#         traj.points.append(point)
#         self.gripper_pub.publish(traj)

#     def open_gripper(self):
#         rospy.loginfo("Opening gripper...")
#         self.send_gripper_command(0.045)
#         rospy.sleep(1.5)

#     def close_gripper(self):
#         rospy.loginfo("Closing gripper...")
#         self.send_gripper_command(0.0)
#         rospy.sleep(1.5)

#     def move_arm_to_carry_pose(self):
#         rospy.loginfo("Moving arm to carry pose...")

#         joint_goal = {
#             "torso_lift_joint": 0.15,
#             "arm_1_joint": 0.20,
#             "arm_2_joint": -1.30,
#             "arm_3_joint": -0.20,
#             "arm_4_joint": 1.90,
#             "arm_5_joint": -1.57,
#             "arm_6_joint": 1.30,
#             "arm_7_joint": 0.00,
#         }

#         self.arm.set_joint_value_target(joint_goal)
#         success = self.arm.go(wait=True)
#         self.arm.stop()

#         if success:
#             rospy.loginfo("Reached carry pose.")
#         else:
#             rospy.logwarn("Failed to reach carry pose.")

#         return success

#     def pick_cloth(self, grasp_target):
#         rospy.loginfo(
#             "Raw grasp target: x=%.3f, y=%.3f, z=%.3f",
#             grasp_target.point.x,
#             grasp_target.point.y,
#             grasp_target.point.z
#         )

#         # Front-insertion grasp strategy:
#         # pre_grasp is outside Box A, grasp only moves forward along x.
#         # This avoids the previous top-down motion that can collide with the box rim.
#         pre_grasp = self.make_pose(grasp_target, x_offset=-0.22, z_offset=0.03)
#         grasp = self.make_pose(grasp_target, x_offset=-0.08, z_offset=0.03)
#         lift = self.make_pose(grasp_target, x_offset=-0.18, z_offset=0.18)

#         rospy.loginfo(
#             "Safe pre-grasp: x=%.3f, y=%.3f, z=%.3f",
#             pre_grasp.pose.position.x,
#             pre_grasp.pose.position.y,
#             pre_grasp.pose.position.z
#         )
#         rospy.loginfo(
#             "Safe grasp: x=%.3f, y=%.3f, z=%.3f",
#             grasp.pose.position.x,
#             grasp.pose.position.y,
#             grasp.pose.position.z
#         )

#         self.open_gripper()

#         if not self.move_to_pose(pre_grasp, "pre-grasp pose"):
#             return False

#         if not self.move_to_pose(grasp, "grasp pose"):
#             return False

#         self.close_gripper()

#         if not self.move_to_pose(lift, "lift pose"):
#             return False

#         self.move_arm_to_carry_pose()
#         return True

#     def place_cloth(self, drop_target):
#         pre_drop = self.make_pose(drop_target, z_offset=0.25)
#         drop = self.make_pose(drop_target, z_offset=0.12)

#         if not self.move_to_pose(pre_drop, "pre-drop pose"):
#             return False

#         if not self.move_to_pose(drop, "drop pose"):
#             return False

#         self.open_gripper()

#         if not self.move_to_pose(pre_drop, "retreat pose"):
#             return False

#         self.move_arm_to_carry_pose()
#         return True

#     def run(self):
#         rospy.sleep(2.0)

#         # 1. Read initial grasp target from middle position
#         initial_grasp = self.wait_for_target("grasp")
#         if initial_grasp is None:
#             return

#         # 2. Move laterally to Box A front
#         self.lateral_move_to_target_y(initial_grasp)

#         # 2.5 Move closer to Box A
#         self.drive_forward_distance(-0.10)

#         # 3. Wait for a NEW grasp target after base motion
#         self.latest_grasp = None
#         self.latest_drop = None
#         move_finish_time = rospy.Time.now()
#         rospy.sleep(2.0)

#         grasp_target = self.wait_for_fresh_target("grasp", move_finish_time)
#         if grasp_target is None:
#             return

#         self.executing = True

#         if not self.pick_cloth(grasp_target):
#             rospy.logwarn("Pick cloth failed.")
#             self.executing = False
#             return

#         self.executing = False
#         rospy.sleep(1.0)

#         # 4. Move from Box A to Box B
#         self.move_from_box_a_to_box_b()

#         # 5. Wait for a NEW drop target after base motion
#         self.latest_grasp = None
#         self.latest_drop = None
#         move_finish_time = rospy.Time.now()
#         rospy.sleep(2.0)

#         drop_target = self.wait_for_fresh_target("drop", move_finish_time)
#         if drop_target is None:
#             return

#         self.executing = True

#         if not self.place_cloth(drop_target):
#             rospy.logwarn("Place cloth failed.")
#             self.executing = False
#             return

#         self.executing = False
#         self.stop_base()

#         rospy.loginfo("Laundry pick-and-place task completed.")
#         rospy.spin()


# if __name__ == "__main__":
#     try:
#         node = LaundryManipulationNode()
#         node.run()
#     except rospy.ROSInterruptException:
#         pass























#!/usr/bin/env python3

import sys
import rospy
import moveit_commander

from geometry_msgs.msg import PointStamped, PoseStamped, Twist
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint


class LaundryManipulationNode:
    def __init__(self):
        rospy.init_node("laundry_manipulation_node")

        self.latest_grasp = None
        self.latest_drop = None
        self.executing = False

        self.drive_speed = rospy.get_param("~drive_speed", 0.05)
        self.turn_speed = rospy.get_param("~turn_speed", 0.25)
        self.turn_90_duration = rospy.get_param("~turn_90_duration", 6.28)
        self.box_distance = rospy.get_param("~box_distance", 0.72)
        self.target_frame = rospy.get_param("~target_frame", "base_footprint")

        rospy.Subscriber("/tiago_vision/clothes_grasp_target", PointStamped, self.grasp_cb)
        rospy.Subscriber("/tiago_vision/clothes_drop_target", PointStamped, self.drop_cb)

        self.cmd_vel_pub = rospy.Publisher("/mobile_base_controller/cmd_vel", Twist, queue_size=1)
        self.gripper_pub = rospy.Publisher("/gripper_controller/command", JointTrajectory, queue_size=1)

        moveit_commander.roscpp_initialize(sys.argv)
        self.arm = moveit_commander.MoveGroupCommander("arm_torso")
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

    def lateral_move_to_target_y(self, target):
        desired_y = 0.00
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
        rospy.loginfo("Moving from Box A to Box B...")

        self.turn_right_90()
        self.drive_forward_distance(self.box_distance - 0.00)
        # self.turn_left_90()
        rospy.loginfo("Turning left 90 degrees...")
        self.turn_for_time(
            abs(self.turn_speed),
            self.turn_90_duration * 90.0 / 90.0
        )

        rospy.sleep(2.0)

    def make_pose(self, point_msg, x_offset=0.0, y_offset=0.0, z_offset=0.0):
        pose = PoseStamped()

        # Force current time and base_footprint to avoid old TF timestamp problems.
        pose.header.frame_id = self.target_frame
        pose.header.stamp = rospy.Time.now()

        # Do not fully trust the detected z value. Sometimes the point cloud detects
        # the box edge or the upper surface instead of the cloth center.
        safe_z = max(min(point_msg.point.z, 0.55), 0.40)

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

        # Front-insertion grasp strategy:
        # pre_grasp is outside Box A, grasp only moves forward along x.
        # This avoids the previous top-down motion that can collide with the box rim.
        pre_grasp = self.make_pose(grasp_target, x_offset=-0.22, z_offset=0.03)
        grasp = self.make_pose(grasp_target, x_offset=-0.08, z_offset=0.03)
        lift = self.make_pose(grasp_target, x_offset=-0.18, z_offset=0.18)

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

        if not self.move_to_pose(grasp, "grasp pose"):
            return False

        self.close_gripper()

        if not self.move_to_pose(lift, "lift pose"):
            return False

        self.move_arm_to_carry_pose()
        return True

    def place_cloth(self, drop_target):
        pre_drop = self.make_pose(drop_target, z_offset=0.25)
        drop = self.make_pose(drop_target, z_offset=0.12)

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

        # 1. Read initial grasp target from middle position
        initial_grasp = self.wait_for_target("grasp")
        if initial_grasp is None:
            return

        # 2. Move laterally to Box A front
        self.lateral_move_to_target_y(initial_grasp)

        # 2.5 Move closer to Box A
        self.drive_forward_distance(-0.10)

        # 3. Wait for a NEW grasp target after base motion
        self.latest_grasp = None
        self.latest_drop = None
        move_finish_time = rospy.Time.now()
        rospy.sleep(2.0)

        grasp_target = self.wait_for_fresh_target("grasp", move_finish_time)
        if grasp_target is None:
            return

        self.executing = True

        if not self.pick_cloth(grasp_target):
            rospy.logwarn("Pick cloth failed.")
            self.executing = False
            return

        self.executing = False
        rospy.sleep(1.0)

        # 4. Move from Box A to Box B
        self.move_from_box_a_to_box_b()
        self.drive_forward_distance(0.20)

        # 5. Wait for a NEW drop target after base motion
        self.latest_grasp = None
        self.latest_drop = None
        move_finish_time = rospy.Time.now()
        rospy.sleep(2.0)

        drop_target = self.wait_for_fresh_target("drop", move_finish_time)
        if drop_target is None:
            return

        self.executing = True

        if not self.place_cloth(drop_target):
            rospy.logwarn("Place cloth failed.")
            self.executing = False
            return

        self.executing = False
        self.stop_base()

        rospy.loginfo("Laundry pick-and-place task completed.")
        rospy.spin()


if __name__ == "__main__":
    try:
        node = LaundryManipulationNode()
        node.run()
    except rospy.ROSInterruptException:
        pass























# #!/usr/bin/env python3

# import sys
# import rospy
# import moveit_commander
# import os
# import std_srvs.srv

# from geometry_msgs.msg import PointStamped, PoseStamped, Twist
# from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint


# class LaundryManipulationNode:
#     def __init__(self):
#         rospy.init_node("laundry_manipulation_node")

#         self.latest_grasp = None
#         self.latest_drop = None
#         self.executing = False

#         self.drive_speed = rospy.get_param("~drive_speed", 0.05)
#         self.turn_speed = rospy.get_param("~turn_speed", 0.25)
#         self.turn_90_duration = rospy.get_param("~turn_90_duration", 6.28)
#         self.box_distance = rospy.get_param("~box_distance", 0.72)

#         rospy.Subscriber("/tiago_vision/clothes_grasp_target", PointStamped, self.grasp_cb)
#         rospy.Subscriber("/tiago_vision/clothes_drop_target", PointStamped, self.drop_cb)

#         self.cmd_vel_pub = rospy.Publisher("/mobile_base_controller/cmd_vel", Twist, queue_size=1)
#         self.gripper_pub = rospy.Publisher("/gripper_controller/command", JointTrajectory, queue_size=1)

#         moveit_commander.roscpp_initialize(sys.argv)
#         self.arm = moveit_commander.MoveGroupCommander("arm_torso")
        
#         # --- MOVED TOLERANCE SETTINGS HERE, AFTER SELF.ARM IS CREATED ---
#         self.arm.set_goal_position_tolerance(0.3) 
#         self.arm.set_goal_orientation_tolerance(1.0)
#         # -------------------------------------------------------------
        
#         self.arm.set_planning_time(10.0)
#         self.arm.set_num_planning_attempts(10)
#         self.arm.set_max_velocity_scaling_factor(0.3)
#         self.arm.set_max_acceleration_scaling_factor(0.3)

#         rospy.loginfo("Laundry manipulation node initialized.")

#     def grasp_cb(self, msg):
#         if not self.executing:
#             self.latest_grasp = msg

#     def drop_cb(self, msg):
#         if not self.executing:
#             self.latest_drop = msg

#     def stop_base(self):
#         self.cmd_vel_pub.publish(Twist())
#         rospy.sleep(0.5)

#     def drive_for_time(self, linear_x, duration):
#         cmd = Twist()
#         cmd.linear.x = linear_x
#         rate = rospy.Rate(10)
#         start = rospy.Time.now()

#         while (rospy.Time.now() - start).to_sec() < duration and not rospy.is_shutdown():
#             self.cmd_vel_pub.publish(cmd)
#             rate.sleep()

#         self.stop_base()

#     def turn_for_time(self, angular_z, duration):
#         cmd = Twist()
#         cmd.angular.z = angular_z
#         rate = rospy.Rate(10)
#         start = rospy.Time.now()

#         while (rospy.Time.now() - start).to_sec() < duration and not rospy.is_shutdown():
#             self.cmd_vel_pub.publish(cmd)
#             rate.sleep()

#         self.stop_base()

#     def turn_left_90(self):
#         rospy.loginfo("Turning left 90 degrees...")
#         self.turn_for_time(abs(self.turn_speed), self.turn_90_duration)

#     def turn_right_90(self):
#         rospy.loginfo("Turning right 90 degrees...")
#         self.turn_for_time(-abs(self.turn_speed), self.turn_90_duration)

#     def drive_forward_distance(self, distance):
#         if distance <= 0.0:
#             return

#         duration = distance / self.drive_speed
#         rospy.loginfo("Driving forward %.3f m for %.2f seconds...", distance, duration)
#         self.drive_for_time(self.drive_speed, duration)

#     def wait_for_target(self, target_type):
#         rospy.loginfo("Waiting for %s target...", target_type)
#         rate = rospy.Rate(10)

#         while not rospy.is_shutdown():
#             target = self.latest_grasp if target_type == "grasp" else self.latest_drop
#             if target is not None:
#                 rospy.loginfo(
#                     "Got %s target: x=%.3f, y=%.3f, z=%.3f",
#                     target_type,
#                     target.point.x,
#                     target.point.y,
#                     target.point.z
#                 )
#                 return target
#             rate.sleep()

#         return None

#     def lateral_move_to_target_y(self, target):
#         y = target.point.y

#         rospy.loginfo("Lateral correction using target y=%.3f", y)

#         if abs(y) < 0.05:
#             rospy.loginfo("Target already close to y=0. No lateral move needed.")
#             return

#         if y > 0.0:
#             self.turn_left_90()
#             self.drive_forward_distance(abs(y))
#             self.turn_right_90()
#         else:
#             self.turn_right_90()
#             self.drive_forward_distance(abs(y))
#             self.turn_left_90()

#         rospy.sleep(2.0)

#     def move_from_box_a_to_box_b(self):
#         rospy.loginfo("Moving from Box A to Box B...")

#         self.turn_right_90()
#         self.drive_forward_distance(self.box_distance)
#         self.turn_left_90()

#         rospy.sleep(2.0)

#     def lock_target(self, target_type):
#         target = self.latest_grasp if target_type == "grasp" else self.latest_drop

#         if target is None:
#             rospy.logerr("Cannot lock %s target. No target received.", target_type)
#             return None

#         locked = PointStamped()
#         locked.header = target.header
#         locked.point = target.point

#         rospy.loginfo(
#             "Locked %s target: x=%.3f, y=%.3f, z=%.3f",
#             target_type,
#             locked.point.x,
#             locked.point.y,
#             locked.point.z
#         )

#         return locked

#     def make_pose(self, point_msg, z_offset, approach='top'):
#         pose = PoseStamped()
#         pose.header.frame_id = "base_link"
#         pose.header.stamp = rospy.Time.now()

#         pose.pose.position.x = point_msg.point.x
#         pose.pose.position.y = point_msg.point.y
#         pose.pose.position.z = point_msg.point.z + z_offset

#         if approach == 'top':
#             # Straight down — for Box B (open top)
#             pose.pose.orientation.x = 0.0
#             pose.pose.orientation.y = 0.0
#             pose.pose.orientation.z = 0.3571
#             pose.pose.orientation.w = 0.3571
#         elif approach == 'front':
#             # Horizontal forward — for Box A (open front)
#             pose.pose.orientation.x = 0.0
#             pose.pose.orientation.y = 0.707
#             pose.pose.orientation.z = 0.0
#             pose.pose.orientation.w = 0.707

#         return pose
        
#         rospy.loginfo("Planning to pose: frame=%s x=%.3f y=%.3f z=%.3f",
#             pre_grasp.header.frame_id,
#             pre_grasp.pose.position.x,
#             pre_grasp.pose.position.y,
#             pre_grasp.pose.position.z)
    
#     def move_to_pose(self, pose, label):
#         rospy.loginfo("Moving to %s...", label)

#         self.arm.set_pose_target(pose)
#         success = self.arm.go(wait=True)

#         self.arm.stop()
#         self.arm.clear_pose_targets()

#         if success:
#             rospy.loginfo("Reached %s.", label)
#         else:
#             rospy.logwarn("Failed to reach %s.", label)

#         return success

#     def send_gripper_command(self, finger_position):
#         traj = JointTrajectory()
#         traj.joint_names = [
#             "gripper_left_finger_joint",
#             "gripper_right_finger_joint"
#         ]

#         point = JointTrajectoryPoint()
#         point.positions = [finger_position, finger_position]
#         point.velocities = [0.0, 0.0]
#         point.time_from_start = rospy.Duration(1.0)

#         traj.points.append(point)
#         self.gripper_pub.publish(traj)

#     def open_gripper(self):
#         rospy.loginfo("Opening gripper...")
#         self.send_gripper_command(0.045)
#         rospy.sleep(1.5)

#     def close_gripper(self):
#         rospy.loginfo("Closing gripper...")
#         self.send_gripper_command(0.0)
#         rospy.sleep(1.5)

#     def move_arm_to_carry_pose(self):
#         rospy.loginfo("Moving arm to carry pose...")

#         joint_goal = {
#             "torso_lift_joint": 0.15,
#             "arm_1_joint": 0.20,
#             "arm_2_joint": -1.30,
#             "arm_3_joint": -0.20,
#             "arm_4_joint": 1.90,
#             "arm_5_joint": -1.57,
#             "arm_6_joint": 1.30,
#             "arm_7_joint": 0.00,
#         }

#         self.arm.set_joint_value_target(joint_goal)
#         success = self.arm.go(wait=True)
#         self.arm.stop()

#         if success:
#             rospy.loginfo("Reached carry pose.")
#         else:
#             rospy.logwarn("Failed to reach carry pose.")

#         return success
#     def tilt_head_down(self):
#         rospy.loginfo("Tilting head down to look at the boxes...")
#         pub = rospy.Publisher("/head_controller/command", JointTrajectory, queue_size=1)
        
#         # Wait for the publisher to actually connect to Gazebo!
#         rospy.sleep(1.0) 
        
#         traj = JointTrajectory()
#         traj.joint_names = ["head_1_joint", "head_2_joint"]
        
#         point = JointTrajectoryPoint()
#         # Using -0.6 so the blue cone doesn't clip under the box!
#         point.positions = [0.0, -0.6] 
#         point.velocities = [0.0, 0.0]
#         point.time_from_start = rospy.Duration(1.5)
        
#         traj.points.append(point)
#         pub.publish(traj)
#         rospy.sleep(2.0) # Wait for head motion to complete

#     def prepare_for_grasp(self):
#         rospy.loginfo("Raising torso for better downward reachability...")
#         joint_goal = self.arm.get_current_joint_values()
#         # torso_lift_joint is usually index 0 in the arm_torso group
#         joint_goal[0] = 0.30  
#         self.arm.set_joint_value_target(joint_goal)
#         self.arm.go(wait=True)
#         self.arm.stop()

#     def pick_cloth(self, grasp_target):
#         rospy.loginfo("Target locked. Clearing octomap...")
#         try:
#             rospy.wait_for_service('/clear_octomap', timeout=2.0)
#             rospy.ServiceProxy('/clear_octomap', std_srvs.srv.Empty)()
#         except (rospy.ServiceException, rospy.ROSException) as e:
#             rospy.logwarn("Could not clear octomap: %s", e)

#         # Box A is front-opening: approach horizontally along X axis
#         # Pre-grasp: stop in front of the opening, z at cloth height
#         pre_grasp = self.make_pose(grasp_target, 0.0, approach='front')
#         pre_grasp.pose.position.x = grasp_target.point.x - 0.15  # 15cm in front of target

#         # Grasp: reach inside the box
#         grasp = self.make_pose(grasp_target, 0.0, approach='front')
#         grasp.pose.position.x = grasp_target.point.x              # at the cloth

#         # Lift: raise straight up to clear the box rim before retreating
#         lift = self.make_pose(grasp_target, 0.25, approach='front')
#         lift.pose.position.x = grasp_target.point.x - 0.10       # pull back slightly

#         rospy.loginfo("Pre-grasp: x=%.3f y=%.3f z=%.3f",
#             pre_grasp.pose.position.x,
#             pre_grasp.pose.position.y,
#             pre_grasp.pose.position.z)

#         self.open_gripper()

#         if not self.move_to_pose(pre_grasp, "pre-grasp pose"):
#             return False
#         if not self.move_to_pose(grasp, "grasp pose"):
#             return False

#         self.close_gripper()

#         if not self.move_to_pose(lift, "lift pose"):
#             return False

#         self.move_arm_to_carry_pose()
#         return True

#     def place_cloth(self, drop_target):
#         pre_drop = self.make_pose(drop_target, 0.30, approach='top')  # clear the rim
#         drop     = self.make_pose(drop_target, 0.08, approach='top')  # descend inside

#         if not self.move_to_pose(pre_drop, "pre-drop pose"):
#             return False
#         if not self.move_to_pose(drop, "drop pose"):
#             return False

#         self.open_gripper()

#         if not self.move_to_pose(pre_drop, "retreat pose"):
#             return False

#         self.move_arm_to_carry_pose()
#         return True

#     def run(self):
#         rospy.sleep(2.0)

#         self.tilt_head_down()

#         # 1. Read initial grasp target from middle position
#         initial_grasp = self.wait_for_target("grasp")
#         if initial_grasp is None:
#             return

#         # 2. Move laterally to Box A front
#         self.lateral_move_to_target_y(initial_grasp)

#         # 3. Read new grasp target and pick cloth
#         self.latest_grasp = None
#         rospy.sleep(2.0)

#         grasp_target = self.wait_for_target("grasp")
#         if grasp_target is None:
#             return
        
#         # 1. Calculate finite distance (with a 10% boost for Gazebo wheel slip)
#         distance_to_close = grasp_target.point.x - 0.68
#         if distance_to_close > 0.02:
#             adjusted_dist = distance_to_close * 1.10 
#             rospy.loginfo("Target is %.2fm away. Driving forward %.2fm...", grasp_target.point.x, adjusted_dist)
#             self.drive_forward_distance(adjusted_dist)

#             grasp_target.point.x -= adjusted_dist
#             rospy.loginfo("Math update: Target is now estimated at X=%.3fm", grasp_target.point.x)
#             rospy.sleep(1.0)
        
#         rospy.loginfo("Grasp target before pick: x=%.3f y=%.3f z=%.3f",
#             grasp_target.point.x,
#             grasp_target.point.y,
#             grasp_target.point.z)

#         self.prepare_for_grasp()
        
#         self.executing = True
#         if not self.pick_cloth(grasp_target):
#             rospy.logwarn("Pick cloth failed.")
#             self.executing = False
#             return

#         self.executing = False
#         rospy.sleep(1.0)

#         # 4. Move from Box A to Box B
#         self.move_from_box_a_to_box_b()

#         # 5. Read new drop target and place cloth
#         self.latest_drop = None
#         rospy.sleep(2.0)

#         drop_target = self.wait_for_target("drop")
#         if drop_target is None:
#             return
        
#         # 1. Calculate finite distance (with a 10% boost for Gazebo wheel slip)
#         distance_to_close = drop_target.point.x - 0.68
#         if distance_to_close > 0.02:
#             adjusted_dist = distance_to_close * 1.10 
#             rospy.loginfo("Drop target is %.2fm away. Driving forward %.2fm...", drop_target.point.x, adjusted_dist)
#             self.drive_forward_distance(adjusted_dist)

#             drop_target.point.x -= adjusted_dist
#             rospy.loginfo("Math update: Target is now estimated at X=%.3fm", drop_target.point.x)
#             rospy.sleep(1.0)

#         self.prepare_for_grasp()
        
#         self.executing = True
#         if not self.place_cloth(drop_target):
#             rospy.logwarn("Place cloth failed.")
#             self.executing = False
#             return

#         self.executing = False
#         self.stop_base()

#         rospy.loginfo("Laundry pick-and-place task completed.")
#         rospy.spin()


# if __name__ == "__main__":
#     try:
#         node = LaundryManipulationNode()
#         node.run()
#     except rospy.ROSInterruptException:
#         pass
