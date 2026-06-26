cmake_minimum_required(VERSION 3.0.2)
project(tiago_control)

find_package(catkin REQUIRED COMPONENTS
  rospy
  std_msgs
  geometry_msgs
  trajectory_msgs
  control_msgs
  actionlib
  moveit_msgs
)

catkin_package()

catkin_install_python(PROGRAMS
  scripts/manipulation_node.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
