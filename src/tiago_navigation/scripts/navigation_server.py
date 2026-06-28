#!/usr/bin/env python3

import math

import rospy
import actionlib
import tf
import tf.transformations

from actionlib_msgs.msg import GoalStatus
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal

from laundry_navigation.srv import GoToPose, GoToPoseResponse


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

        self.goal_timeout = rospy.get_param("~goal_timeout", 90.0)
        self.xy_tolerance = rospy.get_param("~xy_tolerance", 0.15)
        self.yaw_tolerance = rospy.get_param("~yaw_tolerance", 0.35)

        self.tf_listener = tf.TransformListener()

        rospy.loginfo("Waiting for move_base action server: %s", self.move_base_action)
        self.client = actionlib.SimpleActionClient(self.move_base_action, MoveBaseAction)
        self.client.wait_for_server()
        rospy.loginfo("Connected to move_base action server.")

        self.service = rospy.Service(
            "/laundry_navigation/go_to_pose",
            GoToPose,
            self.handle_go_to_pose,
        )

        rospy.loginfo("Laundry navigation service is ready: /laundry_navigation/go_to_pose")

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

    def is_goal_reached(self, x, y, yaw, frame_id):
        pose = self.get_robot_pose(frame_id)
        if pose is None:
            return False

        robot_x, robot_y, robot_yaw = pose

        dx = x - robot_x
        dy = y - robot_y
        dist = math.sqrt(dx * dx + dy * dy)
        yaw_error = abs(normalize_angle(yaw - robot_yaw))

        rospy.loginfo(
            "Goal check: dist=%.3f m, yaw_error=%.3f rad",
            dist,
            yaw_error,
        )

        return dist <= self.xy_tolerance and yaw_error <= self.yaw_tolerance

    def handle_go_to_pose(self, request):
        frame_id = request.frame_id.strip() if request.frame_id.strip() else self.default_frame

        rospy.loginfo(
            "Navigation request: frame=%s, x=%.3f, y=%.3f, yaw=%.3f rad",
            frame_id,
            request.x,
            request.y,
            request.yaw,
        )

        if self.is_goal_reached(request.x, request.y, request.yaw, frame_id):
            message = "Already within goal tolerance."
            rospy.loginfo(message)
            return GoToPoseResponse(True, message)

        goal = self.make_goal(request.x, request.y, request.yaw, frame_id)
        self.client.send_goal(goal)

        start_time = rospy.Time.now()
        rate = rospy.Rate(5)

        while not rospy.is_shutdown():
            if self.is_goal_reached(request.x, request.y, request.yaw, frame_id):
                self.client.cancel_goal()
                message = "Navigation succeeded by pose tolerance check."
                rospy.loginfo(message)
                return GoToPoseResponse(True, message)

            state = self.client.get_state()

            if state == GoalStatus.SUCCEEDED:
                message = "Navigation succeeded by move_base."
                rospy.loginfo(message)
                return GoToPoseResponse(True, message)

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
                return GoToPoseResponse(False, message)

            elapsed = (rospy.Time.now() - start_time).to_sec()
            if elapsed > self.goal_timeout:
                self.client.cancel_goal()
                message = "Navigation timeout after %.1f seconds." % self.goal_timeout
                rospy.logwarn(message)
                return GoToPoseResponse(False, message)

            rate.sleep()

        return GoToPoseResponse(False, "ROS shutdown.")


if __name__ == "__main__":
    server = LaundryNavigationServer()
    rospy.spin()
