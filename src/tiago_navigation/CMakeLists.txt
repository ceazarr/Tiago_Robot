cmake_minimum_required(VERSION 3.0.2)
project(laundry_navigation)

find_package(catkin REQUIRED COMPONENTS
  rospy
  geometry_msgs
  move_base_msgs
  actionlib
  actionlib_msgs
  message_generation
  tf
)

add_service_files(
  FILES
  GoToPose.srv
  GoToNamedPose.srv
  GoToTargetFront.srv
)

generate_messages(
  DEPENDENCIES
  geometry_msgs
)

catkin_package(
  CATKIN_DEPENDS
    rospy
    geometry_msgs
    move_base_msgs
    actionlib
    actionlib_msgs
    message_runtime
    tf
)

catkin_install_python(PROGRAMS
  scripts/navigation_server.py
  scripts/target_front_autonav.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
