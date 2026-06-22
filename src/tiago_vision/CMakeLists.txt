cmake_minimum_required(VERSION 3.0.2)
project(tiago_vision)

find_package(catkin REQUIRED COMPONENTS
  roscpp
  std_msgs
  sensor_msgs
  geometry_msgs
  tf
  pcl_ros
  pcl_conversions
  darknet_ros_msgs
  trajectory_msgs
)

find_package(PCL REQUIRED)

catkin_package(
  CATKIN_DEPENDS roscpp std_msgs sensor_msgs geometry_msgs tf pcl_ros pcl_conversions darknet_ros_msgs trajectory_msgs
)

include_directories(
  ${catkin_INCLUDE_DIRS}
  ${PCL_INCLUDE_DIRS}
)

add_executable(box_object_detector_node
  src/box_object_detector.cpp
)

target_link_libraries(box_object_detector_node
  ${catkin_LIBRARIES}
  ${PCL_LIBRARIES}
)

catkin_install_python(PROGRAMS
  src/yolo_detector.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
