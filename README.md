# TIAGo Laundry Loop Manipulation & Vision

This repository contains the vision-based segmentation, tracking, and closed-loop control nodes for the TIAGo laundry robot.

## Commands to Run the Project

Follow these steps to build the workspace, start the simulation, and launch the vision and control nodes.

---

### 1. Pull the Latest Changes

```bash
git pull
```

### 2. Build the Workspace

Build the Catkin workspace inside the simulation docker container:

```bash
./docker/run_sim.sh -b
```

### 3. Start the Gazebo Simulation

Start the Gazebo laundry room simulation world and spawn the TIAGo robot. This command keeps running in your terminal:

```bash
./docker/run_sim.sh
```

---

### 4. Find the Container ID

Since the simulation is running inside a Docker container, you must run the vision and control nodes inside the same container. 

In a new terminal window on your host machine, find the active container ID:

```bash
docker ps
```
Look for the container image/name starting with `tiago_simulation` or `tiago_tutorials`.

---

### 5. Launch the Vision Node (Terminal A)

In a new terminal window on your host, exec into the container and launch the point-cloud segmentation and tracking node:

```bash
# 1. Enter the running Docker container
docker exec -it <YOUR_CONTAINER_ID> bash

# 2. Source the environment and launch the vision node
source /tiago_public_ws/devel/setup.bash
source devel/setup.bash
roslaunch tiago_vision tiago_vision.launch
```

---

### 6. Launch the Manipulation Control Node (Terminal B)

In another new terminal window on your host, exec into the same container and launch the laundry manipulation node:

```bash
# 1. Enter the running Docker container
docker exec -it <YOUR_CONTAINER_ID> bash

# 2. Source the environment and launch the control node
source /tiago_public_ws/devel/setup.bash
source devel/setup.bash
roslaunch tiago_control manipulation.launch
```
# 3. moving the head downwards 
```bash
rostopic pub /head_controller/command trajectory_msgs/JointTrajectory "header:
  stamp: {secs: 0, nsecs: 0}
joint_names: ['head_1_joint', 'head_2_joint']
points:
- positions: [0.0, -0.7]
  velocities: [0.0, 0.0]
  time_from_start: {secs: 2, nsecs: 0}" -1
```

############################################################### run this to swap the code from the team with mine back ##############################################################################################################################

    mv src sandbox/Ceazar/src && mv sandbox/Ceazar/src_colleagues src     

##############################################################################################################################         
##############################################################################################################################


    python3 src/tiago_vision/src/yolo_onnx_detector.py                     
  _model_path:=/dataset/runs/segment/train/weights/best.onnx               
  _continuous_mode:=true  