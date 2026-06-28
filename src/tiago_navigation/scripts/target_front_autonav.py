#!/usr/bin/env python3

import rospy

from geometry_msgs.msg import PointStamped
from laundry_navigation.srv import GoToTargetFront


class TargetFrontAutoNavigator:
    def __init__(self):
        rospy.init_node("target_front_autonav")

        self.target_topic = rospy.get_param("~target_topic", "/test_basket_target")
        self.standoff_distance = rospy.get_param("~standoff_distance", 0.60)
        self.navigate_once = rospy.get_param("~navigate_once", True)

        self.has_navigated = False

        rospy.loginfo("Waiting for service /laundry_navigation/go_to_target_front")
        rospy.wait_for_service("/laundry_navigation/go_to_target_front")

        self.go_to_target_front = rospy.ServiceProxy(
            "/laundry_navigation/go_to_target_front",
            GoToTargetFront
        )

        rospy.Subscriber(
            self.target_topic,
            PointStamped,
            self.target_callback,
            queue_size=1
        )

        rospy.loginfo("Target-front auto navigator is ready.")
        rospy.loginfo("Subscribing target topic: %s", self.target_topic)
        rospy.loginfo("Standoff distance: %.2f m", self.standoff_distance)

    def target_callback(self, msg):
        if self.navigate_once and self.has_navigated:
            return

        rospy.loginfo(
            "Received target: frame=%s, x=%.3f, y=%.3f, z=%.3f",
            msg.header.frame_id,
            msg.point.x,
            msg.point.y,
            msg.point.z,
        )

        try:
            response = self.go_to_target_front(msg, self.standoff_distance)

            rospy.loginfo(
                "Navigation result: success=%s, message=%s, goal=(%.3f, %.3f, %.3f)",
                response.success,
                response.message,
                response.goal_x,
                response.goal_y,
                response.goal_yaw,
            )

            self.has_navigated = True

        except rospy.ServiceException as exc:
            rospy.logerr("Failed to call go_to_target_front: %s", exc)


if __name__ == "__main__":
    node = TargetFrontAutoNavigator()
    rospy.spin()
