# RoboCup@Home Tutorial 2 - Gazebo Simulation and Robot Communication
**Authors:** Ceazar Haddad, Yuxiao Wen
**Robot Used:** TIAGo

---
cat <<EOF > README.md
# Assignment Submission - TIAGo Navigation and Planning

## How to Compile
1. Place folders 'tiago_localization' and 'tiago_move' into your catkin workspace 'src' directory.
2. Run in workspace root:
   catkin build
   source devel/setup.bash

## How to Run

### Exercise 2: Localization
1. Start Gazebo/Navigation:
   roslaunch tiago_2dnav_gazebo tiago_navigation.launch public_sim:=true lost:=true map:=<PATH_TO_MAP>
2. Run node:
   roslaunch tiago_localization tiago_localization.launch

### Exercises 3 & 4: Navigation and Motion Planning
1. Ensure robot is localized.
2. Run node:
   roslaunch tiago_move tiago_move.launch

EOF
