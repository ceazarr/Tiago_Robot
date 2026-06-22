#!/bin/bash

# Setup colors for stdout printing
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0;5m' # No Color
BLUE='\033[0;34m'
BOLD='\033[1m'

echo -e "${BLUE}${BOLD}================================================================${NC}"
echo -e "${BLUE}${BOLD}             TIAGo Robot Docker Simulation Manager              ${NC}"
echo -e "${BLUE}${BOLD}================================================================${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}[ERROR] Docker is not installed on this system.${NC}"
    echo -e "${YELLOW}Please install Docker to run this environment. You can install it using:${NC}"
    echo -e "  sudo apt-get update"
    echo -e "  sudo apt-get install -y docker.io"
    echo -e "  sudo systemctl start docker"
    echo -e "  sudo systemctl enable docker"
    echo -e "  sudo usermod -aG docker \$USER  # Log out and back in after this step!"
    exit 1
fi

# Check if current user can run docker without sudo
if docker ps &> /dev/null; then
    DOCKER_CMD="docker"
else
    DOCKER_CMD="sudo docker"
    echo -e "${YELLOW}[WARNING] Permission denied to connect to Docker socket. Using 'sudo docker'...${NC}"
fi

# Check if Docker Compose is installed
if ! $DOCKER_CMD compose version &> /dev/null; then
    echo -e "${RED}[ERROR] Docker Compose is not installed or not available as 'docker compose'.${NC}"
    echo -e "${YELLOW}Please install docker-compose-v2:${NC}"
    echo -e "  sudo apt-get update && sudo apt-get install -y docker-compose-v2"
    exit 1
fi

# Enable local access to the X11 display server for GUI apps (Gazebo/RViz)
if command -v xhost &> /dev/null; then
    echo -e "${GREEN}[INFO] Granting local GUI access via xhost...${NC}"
    xhost +local:root &> /dev/null
else
    echo -e "${YELLOW}[WARNING] 'xhost' utility not found. GUI applications (Gazebo, RViz) may not show up.${NC}"
    echo -e "${YELLOW}Please install it via 'sudo apt-get install x11-xserver-utils' if graphics fail.${NC}"
fi

# Locate script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Print usage information
usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -i, --interactive   Start container and open an interactive bash shell"
    echo "  -b, --build-only    Build the workspace inside the container and exit"
    echo "  -r, --run-only      Skip build and launch the Gazebo simulation directly"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "By default, the script builds the workspace (if needed) and launches the laundry simulation."
}

MODE="auto"
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -i|--interactive) MODE="interactive"; shift ;;
        -b|--build-only) MODE="build"; shift ;;
        -r|--run-only) MODE="run"; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown parameter passed: $1"; usage; exit 1 ;;
    esac
done

if [ "$MODE" = "interactive" ]; then
    echo -e "${GREEN}[INFO] Starting interactive shell inside TIAGo Noetic environment...${NC}"
    echo -e "${YELLOW}To build and run inside the container, execute:${NC}"
    echo -e "  catkin build"
    echo -e "  source /tiago_public_ws/devel/setup.bash"
    echo -e "  source devel/setup.bash"
    echo -e "  roslaunch object_detection_world tiago.launch world_suffix:=laundry_room robot_pos:=\"-x 0.80 -y 0.0 -z 0.0 -Y 1.57\""
    echo ""
    $DOCKER_CMD compose run --rm tiago_simulation bash
elif [ "$MODE" = "build" ]; then
    echo -e "${GREEN}[INFO] Building the workspace inside the container...${NC}"
    $DOCKER_CMD compose run --rm tiago_simulation bash -c "
        source /tiago_public_ws/devel/setup.bash && \
        catkin build
    "
elif [ "$MODE" = "run" ]; then
    echo -e "${GREEN}[INFO] Running Gazebo simulation directly...${NC}"
    $DOCKER_CMD compose run --rm tiago_simulation bash -c "
        source /tiago_public_ws/devel/setup.bash && \
        source devel/setup.bash && \
        roslaunch object_detection_world tiago.launch world_suffix:=laundry_room robot_pos:=\"-x 0.80 -y 0.0 -z 0.0 -Y 1.57\"
    "
else
    # Auto mode: build if devel/setup.bash does not exist, then run
    echo -e "${GREEN}[INFO] Auto-launching simulation environment...${NC}"
    
    # Check if devel/setup.bash exists locally in the workspace (parent of docker directory)
    if [ ! -f "../devel/setup.bash" ]; then
        echo -e "${YELLOW}[INFO] Build files not detected. Initializing catkin build...${NC}"
        $DOCKER_CMD compose run --rm tiago_simulation bash -c "
            source /tiago_public_ws/devel/setup.bash && \
            catkin build
        "
        if [ $? -ne 0 ]; then
            echo -e "${RED}[ERROR] Build failed! Exiting.${NC}"
            exit 1
        fi
    fi
    
    echo -e "${GREEN}[INFO] Launching the Gazebo world and TIAGo robot...${NC}"
    $DOCKER_CMD compose run --rm tiago_simulation bash -c "
        source /tiago_public_ws/devel/setup.bash && \
        source devel/setup.bash && \
        roslaunch object_detection_world tiago.launch world_suffix:=laundry_room robot_pos:=\"-x 0.80 -y 0.0 -z 0.0 -Y 1.57\"
    "
fi
