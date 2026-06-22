1. Extract the folder `Ceazar_Haddad_Yuxiao_Wen_Tutorial4` into the `src` directory of your catkin workspace.
2. Navigate to the root of your workspace (e.g., `cd ~/tiago_ws`).
3. Compile the packages:
   ```bash
   catkin build
   
4. source devel/setup.bash


Task 1: Tiago

1. roslaunch object_detection_world tiago.launch

the file used here: tutorial4.world


2. Point Camera at Table:

rostopic pub /head_controller/command trajectory_msgs/JointTrajectory "header:
  seq: 0
  stamp:
    secs: 0
    nsecs: 0
  frame_id: ''
joint_names:
- 'head_1_joint'
- 'head_2_joint'
points:
- positions: [0.0, -0.7]
  velocities: [0.0, 0.0]
  accelerations: [0.0, 0.0]
  effort: [0.0, 0.0]
  time_from_start: {secs: 1, nsecs: 0}" -1
  
  Task 3: Tiago
  
  in another terminal after sourcing and while running:

  roslaunch object_detection_world tiago.launch
  
  you runfor the detection: 
  
  roslaunch object_detection object_detection.launch
 
 Task 4: Tiago 
 
 for the segmentation:
 roslaunch plane_segmentation plane_segmentation_tiago.launch

to see the results and change the segmantation type you should go to the rviz that is launched from: 
  roslaunch object_detection_world tiago.launch
  
  and change the topic in pointloud2 after adding it
