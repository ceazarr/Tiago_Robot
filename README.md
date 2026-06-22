### Vision (Segmentation and Tracking)

## Commands to run:

  1. Pull the changes:
     
    git pull
  
  3. Build the updated workspace:
  Build the workspace using the simulation docker wrapper:

    ./docker/run_sim.sh -b

  5. Run the simulation:
  6. 
    ./docker/run_sim.sh
  
  7. Launch the node (inside the container shell):
    # 1. Find the active CONTAINER ID (Look for the most recently created 'tiago_tutorials' container)

    docker ps
    
    # 2. Enter the container using that ID
    
    docker exec -it <YOUR_CONTAINER_ID> bash

    # 3. Source the workspace and launch
    
    source /tiago_public_ws/devel/setup.bash
    source devel/setup.bash
    roslaunch tiago_vision tiago_vision.launch
