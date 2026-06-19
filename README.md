# Tiago Robot Final Project

This repository is for the RoboCup@Home final system integration project with the TIAGo robot.

## Yuxiao's update: laundry room Gazebo world

This branch adds a Gazebo world package for the laundry-manipulation scenario.

## Added ROS package

src/tiago_bringup/object_detection_world

This package contains the launch file, RViz config, Gazebo world file, and Gazebo models needed to load the laundry-room scene.

## New world

src/tiago_bringup/object_detection_world/worlds/laundry_room.world

The scene contains:

- two low tables arranged face-to-face,
- a source table with two boxes,
- a front-open black box used as a simplified washing machine,
- an open-top white box used as the laundry basket,
- a simple rigid cloth proxy inside the front-open box,
- an empty destination table,
- simple surrounding walls for a more complete indoor scene.

## New Gazebo models

src/tiago_bringup/object_detection_world/models/low_laundry_table
src/tiago_bringup/object_detection_world/models/front_open_laundry_box
src/tiago_bringup/object_detection_world/models/open_top_laundry_basket
src/tiago_bringup/object_detection_world/models/laundry_cloth_bundle

The cloth is represented by a simple rigid proxy instead of a true deformable cloth model, because deformable cloth physics would make Gazebo simulation and grasping unstable.

## How to run

Inside the TIAGo Docker environment, put this repository in a catkin workspace and build it.

First source the TIAGo workspace and this project workspace:

source /tiago_public_ws/devel/setup.bash
source <your_workspace>/devel/setup.bash

Then launch the laundry world:

roslaunch object_detection_world tiago.launch world_suffix:=laundry_room robot_pos:="-x 0.80 -y 0.0 -z 0.0 -Y 1.57"

The suggested initial robot pose places TIAGo between the two tables, facing the source table and the front-open box.
