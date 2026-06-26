# #!/usr/bin/env python3

# import sys
# import math
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

#         self.desired_x = rospy.get_param("~desired_x", 0.70)
#         self.x_tolerance = rospy.get_param("~x_tolerance", 0.05)
#         self.y_tolerance = rospy.get_param("~y_tolerance", 0.05)

#         self.max_linear_speed = rospy.get_param("~max_linear_speed", 0.08)
#         self.max_angular_speed = rospy.get_param("~max_angular_speed", 0.25)

#         rospy.Subscriber(
#             "/tiago_vision/clothes_grasp_target",
#             PointStamped,
#             self.grasp_cb
#         )

#         rospy.Subscriber(
#             "/tiago_vision/clothes_drop_target",
#             PointStamped,
#             self.drop_cb
#         )

#         self.cmd_vel_pub = rospy.Publisher(
#             "/mobile_base_controller/cmd_vel",
#             Twist,
#             queue_size=1
#         )

#         self.gripper_pub = rospy.Publisher(
#             "/gripper_controller/command",
#             JointTrajectory,
#             queue_size=1
#         )

#         moveit_commander.roscpp_initialize(sys.argv)
#         self.arm = moveit_commander.MoveGroupCommander("arm_torso")
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

#     def align_to_target(self, target_type):
#         rospy.loginfo("Aligning robot base to %s target with one-shot motion...", target_type)

#         rate = rospy.Rate(10)

#         # Wait until target is available
#         while not rospy.is_shutdown():
#             target = self.latest_grasp if target_type == "grasp" else self.latest_drop

#             if target is not None:
#                 break

#             rospy.logwarn_throttle(2.0, "Waiting for %s target...", target_type)
#             rate.sleep()

#         if target is None:
#             return False

#         x = target.point.x
#         y = target.point.y

#         rospy.loginfo(
#             "Initial %s target: x=%.3f, y=%.3f",
#             target_type, x, y
#         )

#         # Step 1: rotate once to face the target
#         angle = math.atan2(y, x)

#         angular_speed = 0.20
#         turn_time = abs(angle) / angular_speed

#         cmd = Twist()
#         cmd.angular.z = angular_speed if angle > 0.0 else -angular_speed

#         rospy.loginfo(
#             "Turning %.3f rad for %.2f seconds...",
#             angle, turn_time
#         )

#         start_time = rospy.Time.now()
#         while (rospy.Time.now() - start_time).to_sec() < turn_time and not rospy.is_shutdown():
#             self.cmd_vel_pub.publish(cmd)
#             rate.sleep()

#         self.stop_base()
#         rospy.sleep(1.0)

#         # Step 2: wait for vision to update after rotation
#         rospy.sleep(2.0)

#         target = self.latest_grasp if target_type == "grasp" else self.latest_drop
#         if target is None:
#             rospy.logerr("No %s target after turning.", target_type)
#             return False

#         x_error = target.point.x - self.desired_x

#         rospy.loginfo(
#             "After turn %s target: x=%.3f, y=%.3f, x_error=%.3f",
#             target_type,
#             target.point.x,
#             target.point.y,
#             x_error
#         )

#         # Step 3: move forward/backward once to desired distance
#         linear_speed = 0.05
#         move_time = abs(x_error) / linear_speed

#         cmd = Twist()
#         cmd.linear.x = linear_speed if x_error > 0.0 else -linear_speed

#         rospy.loginfo(
#             "Moving %.3f m for %.2f seconds...",
#             x_error, move_time
#         )

#         start_time = rospy.Time.now()
#         while (rospy.Time.now() - start_time).to_sec() < move_time and not rospy.is_shutdown():
#             self.cmd_vel_pub.publish(cmd)
#             rate.sleep()

#         self.stop_base()
#         rospy.sleep(1.0)

#         rospy.loginfo("%s target alignment motion finished.", target_type)
#         return True

#     def lock_target(self, target_type):
#         if target_type == "grasp":
#             target = self.latest_grasp
#         else:
#             target = self.latest_drop

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

#     def make_pose(self, point_msg, z_offset):
#         pose = PoseStamped()
#         pose.header.frame_id = point_msg.header.frame_id
#         pose.header.stamp = rospy.Time.now()

#         pose.pose.position.x = point_msg.point.x
#         pose.pose.position.y = point_msg.point.y
#         pose.pose.position.z = point_msg.point.z + z_offset

#         # Simple fixed orientation.
#         # If MoveIt fails, this orientation is the first thing to tune.
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

#     def pick_cloth(self, grasp_target):
#         pre_grasp = self.make_pose(grasp_target, 0.20)
#         grasp = self.make_pose(grasp_target, 0.05)
#         lift = self.make_pose(grasp_target, 0.30)

#         self.open_gripper()

#         if not self.move_to_pose(pre_grasp, "pre-grasp pose"):
#             return False

#         if not self.move_to_pose(grasp, "grasp pose"):
#             return False

#         self.close_gripper()

#         if not self.move_to_pose(lift, "lift pose"):
#             return False

#         return True

#     def place_cloth(self, drop_target):
#         pre_drop = self.make_pose(drop_target, 0.25)
#         drop = self.make_pose(drop_target, 0.12)

#         if not self.move_to_pose(pre_drop, "pre-drop pose"):
#             return False

#         if not self.move_to_pose(drop, "drop pose"):
#             return False

#         self.open_gripper()

#         if not self.move_to_pose(pre_drop, "retreat pose"):
#             return False

#         return True

#     def run(self):
#         rospy.sleep(2.0)

#         self.executing = False

#         # 1. Align base to Box A / clothes
#         if not self.align_to_target("grasp"):
#             return

#         grasp_target = self.lock_target("grasp")
#         if grasp_target is None:
#             return

#         self.executing = True

#         # 2. Pick clothes
#         if not self.pick_cloth(grasp_target):
#             rospy.logwarn("Pick cloth failed.")
#             self.executing = False
#             return

#         self.executing = False
#         rospy.sleep(1.0)

#         # 3. Align base to Box B
#         if not self.align_to_target("drop"):
#             return

#         drop_target = self.lock_target("drop")
#         if drop_target is None:
#             return

#         self.executing = True

#         # 4. Place clothes
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

        rospy.Subscriber("/tiago_vision/clothes_grasp_target", PointStamped, self.grasp_cb)
        rospy.Subscriber("/tiago_vision/clothes_drop_target", PointStamped, self.drop_cb)

        self.cmd_vel_pub = rospy.Publisher("/mobile_base_controller/cmd_vel", Twist, queue_size=1)
        self.gripper_pub = rospy.Publisher("/gripper_controller/command", JointTrajectory, queue_size=1)

        moveit_commander.roscpp_initialize(sys.argv)
        self.arm = moveit_commander.MoveGroupCommander("arm_torso")
        self.arm.set_planning_time(10.0)
        self.arm.set_num_planning_attempts(10)
        self.arm.set_max_velocity_scaling_factor(0.3)
        self.arm.set_max_acceleration_scaling_factor(0.3)

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
        if distance <= 0.0:
            return

        duration = distance / self.drive_speed
        rospy.loginfo("Driving forward %.3f m for %.2f seconds...", distance, duration)
        self.drive_for_time(self.drive_speed, duration)

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

    def lateral_move_to_target_y(self, target):
        y = target.point.y

        rospy.loginfo("Lateral correction using target y=%.3f", y)

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
        self.drive_forward_distance(self.box_distance)
        self.turn_left_90()

        rospy.sleep(2.0)

    def lock_target(self, target_type):
        target = self.latest_grasp if target_type == "grasp" else self.latest_drop

        if target is None:
            rospy.logerr("Cannot lock %s target. No target received.", target_type)
            return None

        locked = PointStamped()
        locked.header = target.header
        locked.point = target.point

        rospy.loginfo(
            "Locked %s target: x=%.3f, y=%.3f, z=%.3f",
            target_type,
            locked.point.x,
            locked.point.y,
            locked.point.z
        )

        return locked

    def make_pose(self, point_msg, z_offset):
        pose = PoseStamped()
        pose.header.frame_id = point_msg.header.frame_id
        pose.header.stamp = rospy.Time.now()

        pose.pose.position.x = point_msg.point.x
        pose.pose.position.y = point_msg.point.y
        pose.pose.position.z = point_msg.point.z + z_offset

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
        pre_grasp = self.make_pose(grasp_target, 0.20)
        grasp = self.make_pose(grasp_target, 0.05)
        lift = self.make_pose(grasp_target, 0.30)

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
        pre_drop = self.make_pose(drop_target, 0.25)
        drop = self.make_pose(drop_target, 0.12)

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

        # 3. Read new grasp target and pick cloth
        self.latest_grasp = None
        rospy.sleep(2.0)

        grasp_target = self.wait_for_target("grasp")
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

        # 5. Read new drop target and place cloth
        self.latest_drop = None
        rospy.sleep(2.0)

        drop_target = self.wait_for_target("drop")
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