#!/usr/bin/env python3

import math

import rospy
import actionlib
import tf
import tf.transformations

from actionlib_msgs.msg import GoalStatus
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal

from laundry_navigation.srv import GoToPose, GoToPoseResponse
from laundry_navigation.srv import GoToNamedPose, GoToNamedPoseResponse
from laundry_navigation.srv import GoToTargetFront, GoToTargetFrontResponse


def normalize_angle(angle):
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


class LaundryNavigationServer:
    def __init__(self):
        rospy.init_node("laundry_navigation_server")

        self.move_base_action = rospy.get_param("~move_base_action", "/move_base")
        self.default_frame = rospy.get_param("~default_frame", "map")
        self.base_frame = rospy.get_param("~base_frame", "base_footprint")

        self.goal_timeout = rospy.get_param("~goal_timeout", 45.0)
        self.xy_tolerance = rospy.get_param("~xy_tolerance", 0.12)
        self.yaw_tolerance = rospy.get_param("~yaw_tolerance", 0.25)
        self.default_standoff = rospy.get_param("~default_standoff_distance", 0.60)

        self.named_poses = rospy.get_param("~named_poses", {})

        self.tf_listener = tf.TransformListener()

        rospy.loginfo("Waiting for move_base action server: %s", self.move_base_action)
        self.client = actionlib.SimpleActionClient(self.move_base_action, MoveBaseAction)
        self.client.wait_for_server()
        rospy.loginfo("Connected to move_base action server.")

        rospy.Service("/laundry_navigation/go_to_pose", GoToPose, self.handle_go_to_pose)
        rospy.Service("/laundry_navigation/go_to_named_pose", GoToNamedPose, self.handle_go_to_named_pose)
        rospy.Service("/laundry_navigation/go_to_target_front", GoToTargetFront, self.handle_go_to_target_front)

        rospy.loginfo("Loaded named poses: %s", list(self.named_poses.keys()))
        rospy.loginfo("Laundry navigation services are ready.")

    def make_goal(self, x, y, yaw, frame_id):
        goal = MoveBaseGoal()
        goal.target_pose.header.stamp = rospy.Time.now()
        goal.target_pose.header.frame_id = frame_id

        goal.target_pose.pose.position.x = x
        goal.target_pose.pose.position.y = y
        goal.target_pose.pose.position.z = 0.0

        q = tf.transformations.quaternion_from_euler(0.0, 0.0, yaw)
        goal.target_pose.pose.orientation.x = q[0]
        goal.target_pose.pose.orientation.y = q[1]
        goal.target_pose.pose.orientation.z = q[2]
        goal.target_pose.pose.orientation.w = q[3]

        return goal

    def get_robot_pose(self, frame_id):
        try:
            self.tf_listener.waitForTransform(
                frame_id,
                self.base_frame,
                rospy.Time(0),
                rospy.Duration(1.0),
            )
            trans, rot = self.tf_listener.lookupTransform(
                frame_id,
                self.base_frame,
                rospy.Time(0),
            )
            _, _, yaw = tf.transformations.euler_from_quaternion(rot)
            return trans[0], trans[1], yaw

        except Exception as exc:
            rospy.logwarn("Could not get robot pose in %s: %s", frame_id, exc)
            return None

    def transform_point_to_map(self, point_stamped):
        try:
            self.tf_listener.waitForTransform(
                self.default_frame,
                point_stamped.header.frame_id,
                rospy.Time(0),
                rospy.Duration(1.0),
            )

            point_stamped.header.stamp = rospy.Time(0)
            target_map = self.tf_listener.transformPoint(self.default_frame, point_stamped)
            return target_map.point.x, target_map.point.y

        except Exception as exc:
            rospy.logwarn("Could not transform target point to %s: %s", self.default_frame, exc)
            return None

    def is_goal_reached(self, x, y, yaw, frame_id):
        pose = self.get_robot_pose(frame_id)
        if pose is None:
            return False

        robot_x, robot_y, robot_yaw = pose

        dx = x - robot_x
        dy = y - robot_y
        dist = math.sqrt(dx * dx + dy * dy)
        yaw_error = abs(normalize_angle(yaw - robot_yaw))

        rospy.loginfo_throttle(
            2.0,
            "Goal check: dist=%.3f m, yaw_error=%.3f rad",
            dist,
            yaw_error,
        )

        return dist <= self.xy_tolerance and yaw_error <= self.yaw_tolerance

    def go_to_pose(self, x, y, yaw, frame_id):
        if self.is_goal_reached(x, y, yaw, frame_id):
            message = "Already within goal tolerance."
            rospy.loginfo(message)
            return True, message

        goal = self.make_goal(x, y, yaw, frame_id)
        self.client.send_goal(goal)

        start_time = rospy.Time.now()
        rate = rospy.Rate(5)

        while not rospy.is_shutdown():
            if self.is_goal_reached(x, y, yaw, frame_id):
                self.client.cancel_goal()
                message = "Navigation succeeded by pose tolerance check."
                rospy.loginfo(message)
                return True, message

            state = self.client.get_state()

            if state == GoalStatus.SUCCEEDED:
                message = "Navigation succeeded by move_base."
                rospy.loginfo(message)
                return True, message

            if state in [
                GoalStatus.ABORTED,
                GoalStatus.REJECTED,
                GoalStatus.PREEMPTED,
                GoalStatus.RECALLED,
                GoalStatus.LOST,
            ]:
                result_text = self.client.get_goal_status_text()
                message = "Navigation failed with state %d: %s" % (state, result_text)
                rospy.logwarn(message)
                return False, message

            elapsed = (rospy.Time.now() - start_time).to_sec()
            if elapsed > self.goal_timeout:
                self.client.cancel_goal()
                message = "Navigation timeout after %.1f seconds." % self.goal_timeout
                rospy.logwarn(message)
                return False, message

            rate.sleep()

        return False, "ROS shutdown."

    def handle_go_to_pose(self, request):
        frame_id = request.frame_id.strip() if request.frame_id.strip() else self.default_frame

        rospy.loginfo(
            "Navigation request: frame=%s, x=%.3f, y=%.3f, yaw=%.3f rad",
            frame_id,
            request.x,
            request.y,
            request.yaw,
        )

        success, message = self.go_to_pose(request.x, request.y, request.yaw, frame_id)
        return GoToPoseResponse(success, message)

    def handle_go_to_named_pose(self, request):
        name = request.name.strip()

        if name not in self.named_poses:
            available = sorted(self.named_poses.keys())
            message = "Unknown named pose '%s'. Available: %s" % (name, available)
            rospy.logwarn(message)
            return GoToNamedPoseResponse(False, message)

        pose = self.named_poses[name]
        x = float(pose["x"])
        y = float(pose["y"])
        yaw = float(pose["yaw"])
        frame_id = str(pose.get("frame_id", self.default_frame))

        rospy.loginfo(
            "Named pose request: %s -> frame=%s, x=%.3f, y=%.3f, yaw=%.3f",
            name,
            frame_id,
            x,
            y,
            yaw,
        )

        success, message = self.go_to_pose(x, y, yaw, frame_id)
        return GoToNamedPoseResponse(success, message)

    def handle_go_to_target_front(self, request):
        standoff = request.standoff_distance
        if standoff <= 0.05:
            standoff = self.default_standoff

        target_xy = self.transform_point_to_map(request.target)
        if target_xy is None:
            return GoToTargetFrontResponse(False, "Could not transform target point to map.", 0.0, 0.0, 0.0)

        robot_pose = self.get_robot_pose(self.default_frame)
        if robot_pose is None:
            return GoToTargetFrontResponse(False, "Could not get robot pose in map.", 0.0, 0.0, 0.0)

        target_x, target_y = target_xy
        robot_x, robot_y, _ = robot_pose

        vx = target_x - robot_x
        vy = target_y - robot_y
        norm = math.sqrt(vx * vx + vy * vy)

        if norm < 0.05:
            return GoToTargetFrontResponse(False, "Target is too close to robot.", 0.0, 0.0, 0.0)

        ux = vx / norm
        uy = vy / norm

        goal_x = target_x - ux * standoff
        goal_y = target_y - uy * standoff
        goal_yaw = math.atan2(target_y - goal_y, target_x - goal_x)

        rospy.loginfo(
            "Target-front request: target=(%.3f, %.3f), robot=(%.3f, %.3f), goal=(%.3f, %.3f, %.3f), standoff=%.3f",
            target_x,
            target_y,
            robot_x,
            robot_y,
            goal_x,
            goal_y,
            goal_yaw,
            standoff,
        )

        success, message = self.go_to_pose(goal_x, goal_y, goal_yaw, self.default_frame)
        return GoToTargetFrontResponse(success, message, goal_x, goal_y, goal_yaw)


if __name__ == "__main__":
    server = LaundryNavigationServer()
    rospy.spin()
