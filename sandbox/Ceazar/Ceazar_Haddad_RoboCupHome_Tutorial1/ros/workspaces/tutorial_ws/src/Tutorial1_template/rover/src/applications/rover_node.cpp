#include <ros/ros.h>

#include <rover/rover.h>

int main( int argc, char** argv )
{
  ros::init(argc, argv, "rover_node");

  rover::Rover rover;

  ros::NodeHandle nh;
  //#>>>>TODO: initialize the rover
  //#>>>>TODO: Check if its return value is true, else stop the node here and search the error
  //#>>>>TODO: call the initialize(...) function
  if(!rover.initialize(nh))
  {
    ROS_ERROR_STREAM("Failed to initialize the rover node");
    return -1;
  }

  ros::Rate rate(60);
  ros::Time time;
  ros::Time prev_time = ros::Time::now();
  ros::Duration duration;

  while(ros::ok())
  {
    time = ros::Time::now();
    duration = time - prev_time;
    prev_time = time;

    rover.update(time, duration);

    ros::spinOnce();
    rate.sleep();
  }

  return 0;
};