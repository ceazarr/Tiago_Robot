# Navigation Module Usage

This module provides navigation support for the laundry task. It can move TIAGo to fixed poses, and it can also move the robot to a pose in front of a target detected by the vision module.

## Main idea

The robot should not rely on detecting the clothes or basket from far away. The intended pipeline is:

```text
navigate to an observation pose
→ vision detects the target
→ navigation receives the target point
→ robot moves to a pose in front of the target
```

The vision module currently publishes target points such as:

```text
/tiago_vision/clothes_grasp_target
/tiago_vision/clothes_drop_target
```

For the navigation part, `/tiago_vision/clothes_drop_target` is used as the target for moving in front of the basket/drop area.

## Start navigation server

```bash
source /tiago_public_ws/devel/setup.bash
source /tiago_robot_ws/devel/setup.bash

roslaunch laundry_navigation laundry_navigation.launch
```

This starts the services:

```text
/laundry_navigation/go_to_pose
/laundry_navigation/go_to_named_pose
/laundry_navigation/go_to_target_front
```

## Move to a named pose

Named poses are stored in:

```text
src/tiago_navigation/config/navigation_poses.yaml
```

Example:

```bash
rosservice call /laundry_navigation/go_to_named_pose "name: 'source_observation'"
```

`source_observation` is the current observation pose in front of the source box. It is mainly used to let the camera see the table and the boxes.

## Move to a given pose

```bash
rosservice call /laundry_navigation/go_to_pose "x: 0.131
y: -0.005
yaw: 2.911
frame_id: 'map'"
```

This sends a goal to `move_base`.

## Move in front of a detected target

The service `/laundry_navigation/go_to_target_front` takes a `PointStamped` target and computes a pose in front of it.

Example:

```bash
rosservice call /laundry_navigation/go_to_target_front "target:
  header:
    frame_id: 'map'
  point:
    x: -0.453
    y: 0.132
    z: 0.0
standoff_distance: 0.60"
```

The robot will try to stand about `0.60 m` away from the target and face it.

## Automatic target navigation

To automatically react to a vision target:

```bash
roslaunch laundry_navigation target_front_autonav.launch target_topic:=/tiago_vision/clothes_drop_target navigate_once:=true
```

Once `/tiago_vision/clothes_drop_target` publishes a point, the node will call `/laundry_navigation/go_to_target_front` automatically.

For testing without vision, use:

```bash
roslaunch laundry_navigation target_front_autonav.launch target_topic:=/test_basket_target navigate_once:=false
```

Then publish a fake target:

```bash
rostopic pub -1 /test_basket_target geometry_msgs/PointStamped "header:
  frame_id: 'map'
point:
  x: -0.453
  y: 0.132
  z: 0.0"
```

## Useful commands

Check robot pose:

```bash
rosrun tf tf_echo map base_footprint
```

Clear costmaps:

```bash
rosservice call /move_base/clear_costmaps
```

Cancel current navigation goal:

```bash
rostopic pub -1 /move_base/cancel actionlib_msgs/GoalID "{}"
```

Check vision target:

```bash
rostopic echo -n 1 /tiago_vision/clothes_drop_target
```

Tilt the head down:

```bash
rostopic pub -1 /head_controller/command trajectory_msgs/JointTrajectory "joint_names:
- 'head_1_joint'
- 'head_2_joint'
points:
- positions: [0.0, -0.8]
  time_from_start:
    secs: 1
    nsecs: 0"
```

## Notes

The fixed poses in `navigation_poses.yaml` are mainly for simulation and debugging. For the final setup, the preferred method is to use the target point published by the vision module and call `go_to_target_front`.

During simulation, Gazebo coordinates and map coordinates are not directly aligned, so Gazebo model positions should not be used directly as map navigation goals.

