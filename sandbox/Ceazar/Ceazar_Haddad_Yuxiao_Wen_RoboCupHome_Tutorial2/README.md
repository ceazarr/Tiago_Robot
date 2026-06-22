# RoboCup@Home Tutorial 2 - Gazebo Simulation and Robot Communication
**Authors:** Ceazar Haddad, Yuxiao Wen
**Robot Used:** TIAGo


## Packages Required
- `ics_gazebo`
- `controllers_tutorials`

---

## Exercise 6.1 - Simulation Scenario
**Robot:** TIAGo
**Package:** `ics_gazebo`

### Compile
```bash
cd /workspaces/tiago/tiago_ws
catkin build ics_gazebo -DCATKIN_ENABLE_TESTING=0
source devel/setup.bash
```

### Run
```bash
roslaunch ics_gazebo tiago.launch world_suffix:=tutorial2
```
Gazebo will open with the scenario including the door model and 10+ objects.

---

## Exercise 6.2 - rviz Configuration
**Robot:** TIAGo
**Package:** `ics_gazebo`

### Run
```bash
roslaunch ics_gazebo tiago.launch world_suffix:=tutorial2
```
rviz opens automatically with all sensors configured:
- Grid
- RobotModel
- Range (sonar)
- LaserScan
- Camera
- DepthCloud

---

## Exercise 6.3 - Head Controller Plugin
**Robot:** TIAGo
**Package:** `controllers_tutorials`

### Compile
```bash
cd /workspaces/tiago/tiago_ws
catkin build controllers_tutorials -DCATKIN_ENABLE_TESTING=0
source devel/setup.bash
```

### Run
Terminal 1 - Launch simulation:
```bash
roslaunch ics_gazebo tiago.launch world_suffix:=tutorial2
```

Terminal 2 - Launch head controller:
```bash
source /workspaces/tiago/tiago_ws/devel/setup.bash
rosrun controller_manager controller_manager kill head_controller
roslaunch controllers_tutorials new_head_controller.launch
```

TIAGo's head will move.

### Stop the controller
```bash
rosrun controller_manager controller_manager kill new_head_controller
```


