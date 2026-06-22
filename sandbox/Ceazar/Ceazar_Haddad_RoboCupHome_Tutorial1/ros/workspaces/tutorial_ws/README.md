# Tutorial 1: ROS Advanced - Rover Controller
**Name:** Ceazar Haddad
**Matriculation Number:** 03752657

## How to Build
1. Unzip `tutorial_ws.zip` into your desired workspace location (e.g., `~/tutorial_ws`).
2. Navigate to the workspace root: `cd ~/tutorial_ws`.
3. Build the workspace: `catkin build`.
4. Source the workspace: `source devel/setup.bash`.

## How to Launch
1. Launch the object server and RViz: `roslaunch object_server object_server.launch`
2. Add obstacles via service: `rosservice call /add_objects "{number: {data: 5}, seed: {data: 0}}"`
3. Launch the rover and controller: `roslaunch rover_controller rover_controller.launch`

## What Happens
- RViz opens showing the rover, obstacles, and vector field visualization.
- The rover controller subscribes to `/move_base_simple/goal` for navigation goals.
- Use RViz's "2D Nav Goal" tool to set goals and watch the rover avoid obstacles.

## Configuration
- Tune gains in `rover_controller/launch/config/config.yaml` (e.g., `k_repulsive`, `lambda_repulsive`).
- Obstacle properties are set in the object_server.

## Troubleshooting
- Ensure all packages build without errors.
- Check ROS topics: `rostopic list` should show `/obstacles`, `/key_vel`, etc.
- If no avoidance, verify obstacle data is published and frames are aligned.
