// #include <ros/ros.h>
// #include <sensor_msgs/PointCloud2.h>
// #include <geometry_msgs/PointStamped.h>
// #include <trajectory_msgs/JointTrajectory.h>
// #include <tf/transform_listener.h>
// #include <tf/transform_broadcaster.h>

// // PCL includes
// #include <pcl_conversions/pcl_conversions.h>
// #include <pcl/point_cloud.h>
// #include <pcl/point_types.h>
// #include <pcl/filters/passthrough.h>
// #include <pcl/filters/crop_box.h>
// #include <pcl/common/centroid.h>
// #include <pcl/common/common.h>
// #include <pcl/sample_consensus/method_types.h>
// #include <pcl/sample_consensus/model_types.h>
// #include <pcl/segmentation/sac_segmentation.h>
// #include <pcl/filters/extract_indices.h>
// #include <pcl/segmentation/extract_clusters.h>
// #include <pcl_ros/transforms.h>
// #include <Eigen/Dense>

// typedef pcl::PointXYZ PointT;
// typedef pcl::PointCloud<PointT> PointCloud;

// class BoxObjectDetector
// {
// private:
//   ros::NodeHandle nh_;
//   ros::Subscriber pc_sub_;
  
//   // Separate Target Publishers
//   ros::Publisher grasp_target_pub_;
//   ros::Publisher drop_target_pub_;
  
//   // Separate PointCloud Publishers
//   ros::Publisher clothes_pc_pub_;
//   ros::Publisher dest_floor_pc_pub_;

//   // Head controller publisher and timer
//   ros::Publisher head_pub_;
//   ros::Timer head_timer_;

//   tf::TransformListener tf_listener_;
//   tf::TransformBroadcaster tf_broadcaster_;

//   // ROS Parameters
//   double workspace_x_min_;
//   double workspace_x_max_;
//   double workspace_y_min_;
//   double workspace_y_max_;
//   double workspace_z_min_;
//   double workspace_z_max_;

//   double table_distance_threshold_;

//   double cluster_tolerance_;
//   int min_cluster_size_;
//   int max_cluster_size_;

//   double wall_margin_;
//   double clothes_float_height_;
//   double box_max_height_;

// public:
//   BoxObjectDetector()
//   {
//     // Load parameters from the ROS parameter server (private namespace)
//     ros::NodeHandle private_nh("~");
//     private_nh.param<double>("workspace_x_min", workspace_x_min_, 0.5);
//     private_nh.param<double>("workspace_x_max", workspace_x_max_, 1.8);
//     private_nh.param<double>("workspace_y_min", workspace_y_min_, -0.8);
//     private_nh.param<double>("workspace_y_max", workspace_y_max_, 0.8);
//     private_nh.param<double>("workspace_z_min", workspace_z_min_, 0.3);
//     private_nh.param<double>("workspace_z_max", workspace_z_max_, 1.2);

//     private_nh.param<double>("table_distance_threshold", table_distance_threshold_, 0.02);

//     private_nh.param<double>("cluster_tolerance", cluster_tolerance_, 0.08);
//     private_nh.param<int>("min_cluster_size", min_cluster_size_, 50);
//     private_nh.param<int>("max_cluster_size", max_cluster_size_, 10000);

//     private_nh.param<double>("wall_margin", wall_margin_, 0.03);
//     private_nh.param<double>("clothes_float_height", clothes_float_height_, 0.02);
//     private_nh.param<double>("box_max_height", box_max_height_, 0.40);

//     // Subscribe to point cloud
//     pc_sub_ = nh_.subscribe("/xtion/depth_registered/points", 1, &BoxObjectDetector::pointCloudCallback, this);

//     // Target Publishers
//     grasp_target_pub_ = nh_.advertise<geometry_msgs::PointStamped>("/tiago_vision/clothes_grasp_target", 1);
//     drop_target_pub_ = nh_.advertise<geometry_msgs::PointStamped>("/tiago_vision/clothes_drop_target", 1);
    
//     // PointCloud Publishers for RViz
//     clothes_pc_pub_ = nh_.advertise<sensor_msgs::PointCloud2>("/tiago_vision/clothes_cloud", 1);
//     dest_floor_pc_pub_ = nh_.advertise<sensor_msgs::PointCloud2>("/tiago_vision/destination_floor_cloud", 1);

//     // Head controller command publisher and timer to automatically look down at startup
//     head_pub_ = nh_.advertise<trajectory_msgs::JointTrajectory>("/head_controller/command", 1);
//     head_timer_ = nh_.createTimer(ros::Duration(2.0), &BoxObjectDetector::tiltHeadCallback, this, true);

//     ROS_INFO("BoxObjectDetector node initialized.");
//   }

//   void tiltHeadCallback(const ros::TimerEvent&)
//   {
//     trajectory_msgs::JointTrajectory traj;
//     traj.joint_names.push_back("head_1_joint");
//     traj.joint_names.push_back("head_2_joint");
    
//     trajectory_msgs::JointTrajectoryPoint point;
//     point.positions.push_back(0.0);
//     point.positions.push_back(-0.7); // Tilt head downwards to face the tables
//     point.velocities.push_back(0.0);
//     point.velocities.push_back(0.0);
//     point.time_from_start = ros::Duration(1.5);
    
//     traj.points.push_back(point);
//     head_pub_.publish(traj);
//     ROS_INFO("Sent head controller command to tilt head downwards.");
//   }

//   void pointCloudCallback(const sensor_msgs::PointCloud2ConstPtr& msg)
//   {
//     // 1. Transform incoming PointCloud to base_footprint frame using latest transform (ros::Time(0))
//     std::string target_frame = "base_footprint";
//     sensor_msgs::PointCloud2 cloud_transformed_msg;
//     try
//     {
//       if (!tf_listener_.waitForTransform(target_frame, msg->header.frame_id, ros::Time(0), ros::Duration(1.0)))
//       {
//         ROS_WARN_THROTTLE(5, "Timed out waiting for transform to %s", target_frame.c_str());
//         return;
//       }
      
//       // Override message stamp to ros::Time(0) to bypass lag/extrapolation issues
//       sensor_msgs::PointCloud2 msg_latest = *msg;
//       msg_latest.header.stamp = ros::Time(0);
      
//       if (!pcl_ros::transformPointCloud(target_frame, msg_latest, cloud_transformed_msg, tf_listener_))
//       {
//         ROS_WARN_THROTTLE(5, "Failed to transform point cloud to %s frame", target_frame.c_str());
//         return;
//       }
//     }
//     catch (tf::TransformException& ex)
//     {
//       ROS_WARN_THROTTLE(5, "TF exception in pointCloudCallback: %s", ex.what());
//       return;
//     }

//     // Convert to PCL PointCloud
//     PointCloud::Ptr cloud(new PointCloud);
//     pcl::fromROSMsg(cloud_transformed_msg, *cloud);

//     if (cloud->empty()) return;

//     // 2. Passthrough Filter to crop the workspace of interest
//     PointCloud::Ptr cropped_cloud(new PointCloud);
//     pcl::CropBox<PointT> workspace_crop;
//     workspace_crop.setInputCloud(cloud);
//     workspace_crop.setMin(Eigen::Vector4f(workspace_x_min_, workspace_y_min_, workspace_z_min_, 1.0));
//     workspace_crop.setMax(Eigen::Vector4f(workspace_x_max_, workspace_y_max_, workspace_z_max_, 1.0));
//     workspace_crop.filter(*cropped_cloud);

//     if (cropped_cloud->empty())
//     {
//       ROS_WARN_THROTTLE(5, "Workspace cropped cloud is empty. Check camera orientation and field of view.");
//       return;
//     }

//     ROS_INFO_THROTTLE(10, "Cropped workspace cloud has %zu points", cropped_cloud->size());

//     // 3. Segment the table plane
//     pcl::ModelCoefficients::Ptr coefficients(new pcl::ModelCoefficients);
//     pcl::PointIndices::Ptr inliers(new pcl::PointIndices);

//     pcl::SACSegmentation<PointT> seg;
//     seg.setOptimizeCoefficients(true);
//     seg.setModelType(pcl::SACMODEL_PLANE);
//     seg.setMethodType(pcl::SAC_RANSAC);
//     seg.setMaxIterations(200);
//     seg.setDistanceThreshold(table_distance_threshold_);

//     seg.setInputCloud(cropped_cloud);
//     seg.segment(*inliers, *coefficients);

//     if (inliers->indices.empty())
//     {
//       ROS_WARN_THROTTLE(5, "Could not estimate table plane.");
//       return;
//     }

//     // Check if the plane is horizontal (normal vector Z component should be close to 1 or -1)
//     double z_normal = std::abs(coefficients->values[2]);
//     if (z_normal < 0.8)
//     {
//       ROS_WARN_THROTTLE(5, "Plane detected is not horizontal (normal z = %.2f). Skipping plane removal.", z_normal);
//       return;
//     }

//     // Extract non-planar points (objects sitting on the table)
//     PointCloud::Ptr table_objects(new PointCloud);
//     pcl::ExtractIndices<PointT> extract_table;
//     extract_table.setInputCloud(cropped_cloud);
//     extract_table.setIndices(inliers);
//     extract_table.setNegative(true); // Remove the table plane
//     extract_table.filter(*table_objects);

//     if (table_objects->empty())
//     {
//       ROS_WARN_THROTTLE(5, "No objects remaining above the table.");
//       return;
//     }

//     // Apply the plane-aligned coordinate transformation to filter out table-relative heights
//     if (!coefficients->values.empty())
//     {
//       Eigen::Vector3f n(coefficients->values[0], coefficients->values[1], coefficients->values[2]);
//       double d = coefficients->values[3];

//       Eigen::Quaternionf Q_plane_base = Eigen::Quaternionf::FromTwoVectors(Eigen::Vector3f(0, 0, 1), n);
//       Eigen::Vector3f t_plane_base = -d * n;

//       Eigen::Affine3f T_plane_base = Eigen::Affine3f::Identity();
//       T_plane_base.rotate(Q_plane_base.toRotationMatrix());
//       T_plane_base.translate(t_plane_base);

//       PointCloud::Ptr transf_cloud(new PointCloud);
//       pcl::transformPointCloud(*table_objects, *transf_cloud, T_plane_base.inverse());

//       PointCloud::Ptr filtered_cloud(new PointCloud);
//       pcl::PassThrough<PointT> pass;
//       pass.setInputCloud(transf_cloud);
//       pass.setFilterFieldName("z");
//       pass.setFilterLimits(0.01, 0.50); // Keep points between 1cm and 50cm above table top surface
//       pass.filter(*filtered_cloud);

//       // Transform back to the base frame
//       table_objects->clear();
//       pcl::transformPointCloud(*filtered_cloud, *table_objects, T_plane_base);
//     }

//     if (table_objects->empty())
//     {
//       ROS_WARN_THROTTLE(5, "No points remaining after table-aligned height filtering.");
//       return;
//     }

//     ROS_INFO_THROTTLE(10, "Table objects cloud has %zu points", table_objects->size());

//     // 4. Euclidean Cluster Extraction to separate the boxes
//     pcl::search::KdTree<PointT>::Ptr tree(new pcl::search::KdTree<PointT>);
//     tree->setInputCloud(table_objects);

//     std::vector<pcl::PointIndices> cluster_indices;
//     pcl::EuclideanClusterExtraction<PointT> ec;
//     ec.setClusterTolerance(cluster_tolerance_);
//     ec.setMinClusterSize(min_cluster_size_);
//     ec.setMaxClusterSize(max_cluster_size_);
//     ec.setSearchMethod(tree);
//     ec.setInputCloud(table_objects);
//     ec.extract(cluster_indices);

//     if (cluster_indices.empty())
//     {
//       ROS_WARN_THROTTLE(5, "No object clusters detected on the table.");
//       return;
//     }

//     ROS_INFO_THROTTLE(10, "Detected %zu clusters on the table.", cluster_indices.size());

//     for (size_t c = 0; c < cluster_indices.size(); ++c)
//     {
//       const auto& indices = cluster_indices[c];
      
//       // Extract cluster cloud
//       PointCloud::Ptr cluster_cloud(new PointCloud);
//       cluster_cloud->header = table_objects->header;
//       for (const auto& idx : indices.indices)
//       {
//         cluster_cloud->points.push_back(table_objects->points[idx]);
//       }

//       // Compute centroid of the cluster in base_footprint frame
//       Eigen::Vector4f cluster_centroid;
//       pcl::compute3DCentroid(*cluster_cloud, cluster_centroid);

//       ROS_INFO_THROTTLE(10, "Cluster %zu size: %zu points, Centroid: [%.3f, %.3f, %.3f]", 
//                         c, cluster_cloud->size(), cluster_centroid[0], cluster_centroid[1], cluster_centroid[2]);

//       // Distinguish classes based on Y position (Y > 0 is left/washing machine box, Y < 0 is right/laundry basket)
//       std::string cluster_class = (cluster_centroid[1] > 0.0) ? "washing machine box" : "laundry basket";

//       // 5. Segment floor plane of the box
//       pcl::ModelCoefficients::Ptr box_floor_coefficients(new pcl::ModelCoefficients);
//       pcl::PointIndices::Ptr box_floor_inliers(new pcl::PointIndices);

//       pcl::SACSegmentation<PointT> box_seg;
//       box_seg.setOptimizeCoefficients(true);
      
//       // Force RANSAC to only find horizontal planes (the floor), ignoring vertical walls
//       box_seg.setModelType(pcl::SACMODEL_PARALLEL_PLANE);
//       box_seg.setAxis(Eigen::Vector3f(0, 0, 1));
//       box_seg.setEpsAngle(0.2); // Allow ~11 degrees of tilt tolerance

//       box_seg.setMethodType(pcl::SAC_RANSAC);
//       box_seg.setMaxIterations(100);
//       box_seg.setDistanceThreshold(0.02);

//       box_seg.setInputCloud(cluster_cloud);
//       box_seg.segment(*box_floor_inliers, *box_floor_coefficients);

//       if (box_floor_inliers->indices.empty())
//       {
//         ROS_WARN("Could not find bottom plane for cluster '%s'.", cluster_class.c_str());
//         continue;
//       }

//       // Extract floor cloud
//       PointCloud::Ptr floor_cloud(new PointCloud);
//       pcl::ExtractIndices<PointT> extract_floor;
//       extract_floor.setInputCloud(cluster_cloud);
//       extract_floor.setIndices(box_floor_inliers);
//       extract_floor.setNegative(false); // Keep floor
//       extract_floor.filter(*floor_cloud);

//       if (floor_cloud->empty()) continue;

//       if (cluster_class == "washing machine box")
//       {
//         // 6a. PCA-based Oriented Bounding Box (OBB) Crop logic
//         Eigen::Vector4f floor_centroid;
//         pcl::compute3DCentroid(*floor_cloud, floor_centroid);

//         Eigen::Matrix3f covariance_matrix;
//         pcl::computeCovarianceMatrixNormalized(*floor_cloud, floor_centroid, covariance_matrix);

//         Eigen::SelfAdjointEigenSolver<Eigen::Matrix3f> eigen_solver(covariance_matrix, Eigen::ComputeEigenvectors);
//         Eigen::Matrix3f eigenvectors = eigen_solver.eigenvectors();

//         // Establish rotation directions (X: primary variance, Y: secondary variance, Z: plane normal)
//         Eigen::Matrix3f rotation;
//         rotation.col(0) = eigenvectors.col(2); // Local X along largest variance
//         rotation.col(1) = eigenvectors.col(1); // Local Y along second largest variance
//         rotation.col(2) = eigenvectors.col(0); // Local Z along plane normal
//         // Ensure right-handed coordinate system
//         // Force the local Z-axis to point UP (align with global +Z)
//         if (rotation.col(2).dot(Eigen::Vector3f(0, 0, 1)) < 0)
//         {
//             rotation.col(2) = -rotation.col(2);
//         }
//         // Ensure right-handed coordinate system after potential Z-flip
//         rotation.col(1) = rotation.col(2).cross(rotation.col(0));

//         // Create the transform from box's local coordinate frame to base_footprint
//         Eigen::Affine3f T_box_base = Eigen::Affine3f::Identity();
//         T_box_base.rotate(rotation);
//         T_box_base.translation() = floor_centroid.head<3>();

//         // Transform cluster and floor to local box coordinate system
//         PointCloud::Ptr cluster_local(new PointCloud);
//         PointCloud::Ptr floor_local(new PointCloud);
//         pcl::transformPointCloud(*cluster_cloud, *cluster_local, T_box_base.inverse());
//         pcl::transformPointCloud(*floor_cloud, *floor_local, T_box_base.inverse());

//         // Perform AABB on local floor cloud to obtain perfectly oriented dimensions
//         PointT min_pt, max_pt;
//         pcl::getMinMax3D(*floor_local, min_pt, max_pt);

//         // Crop the clothes in box's local coordinates
//         pcl::CropBox<PointT> clothes_crop;
//         clothes_crop.setInputCloud(cluster_local);
//         clothes_crop.setMin(Eigen::Vector4f(min_pt.x + wall_margin_, min_pt.y + wall_margin_, min_pt.z + clothes_float_height_, 1.0));
//         clothes_crop.setMax(Eigen::Vector4f(max_pt.x - wall_margin_, max_pt.y - wall_margin_, min_pt.z + box_max_height_, 1.0));

//         PointCloud::Ptr clothes_local(new PointCloud);
//         clothes_crop.filter(*clothes_local);

//         if (clothes_local->empty())
//         {
//           ROS_WARN_THROTTLE(5, "Clothes cloud is empty inside the washing machine box.");
//           continue;
//         }

//         // Transform cropped clothes back to base_footprint frame
//         PointCloud::Ptr clothes_cloud(new PointCloud);
//         pcl::transformPointCloud(*clothes_local, *clothes_cloud, T_box_base);

//         // Compute centroid in base_footprint
//         Eigen::Vector4f clothes_centroid;
//         pcl::compute3DCentroid(*clothes_cloud, clothes_centroid);

//         // Publish target in base_footprint
//         geometry_msgs::PointStamped centroid_msg;
//         centroid_msg.header.frame_id = target_frame;
//         centroid_msg.header.stamp = ros::Time::now();
//         centroid_msg.point.x = clothes_centroid[0];
//         centroid_msg.point.y = clothes_centroid[1];
//         centroid_msg.point.z = clothes_centroid[2];
//         grasp_target_pub_.publish(centroid_msg);

//         // Broadcast TF transform relative to base_footprint
//         tf::Transform transform;
//         transform.setOrigin(tf::Vector3(clothes_centroid[0], clothes_centroid[1], clothes_centroid[2]));
//         transform.setRotation(tf::Quaternion(0, 0, 0, 1));
//         tf_broadcaster_.sendTransform(tf::StampedTransform(transform, ros::Time::now(), target_frame, "clothes_grasp_target"));

//         // Publish clothes point cloud in base_footprint
//         sensor_msgs::PointCloud2 clothes_pc_msg;
//         pcl::toROSMsg(*clothes_cloud, clothes_pc_msg);
//         clothes_pc_msg.header.frame_id = target_frame;
//         clothes_pc_msg.header.stamp = ros::Time::now();
//         clothes_pc_pub_.publish(clothes_pc_msg);

//         ROS_INFO_THROTTLE(2, "Detected clothes grasp target: [%.3f, %.3f, %.3f] in base_footprint", 
//                           clothes_centroid[0], clothes_centroid[1], clothes_centroid[2]);
//       }
//       else if (cluster_class == "laundry basket")
//       {
//         // 6b. Floor centroid is the destination target in base_footprint
//         Eigen::Vector4f floor_centroid;
//         pcl::compute3DCentroid(*floor_cloud, floor_centroid);

//         // Publish target in base_footprint
//         geometry_msgs::PointStamped centroid_msg;
//         centroid_msg.header.frame_id = target_frame;
//         centroid_msg.header.stamp = ros::Time::now();
//         centroid_msg.point.x = floor_centroid[0];
//         centroid_msg.point.y = floor_centroid[1];
//         centroid_msg.point.z = floor_centroid[2];
//         drop_target_pub_.publish(centroid_msg);

//         // Broadcast TF transform relative to base_footprint
//         tf::Transform transform;
//         transform.setOrigin(tf::Vector3(floor_centroid[0], floor_centroid[1], floor_centroid[2]));
//         transform.setRotation(tf::Quaternion(0, 0, 0, 1));
//         tf_broadcaster_.sendTransform(tf::StampedTransform(transform, ros::Time::now(), target_frame, "clothes_drop_target"));

//         // Publish Floor PointCloud in base_footprint
//         sensor_msgs::PointCloud2 floor_pc_msg;
//         pcl::toROSMsg(*floor_cloud, floor_pc_msg);
//         floor_pc_msg.header.frame_id = target_frame;
//         floor_pc_msg.header.stamp = ros::Time::now();
//         dest_floor_pc_pub_.publish(floor_pc_msg);

//         ROS_INFO_THROTTLE(2, "Detected clothes drop target: [%.3f, %.3f, %.3f] in base_footprint", 
//                           floor_centroid[0], floor_centroid[1], floor_centroid[2]);
//       }
//     }
//   }
// };

// int main(int argc, char** argv)
// {
//   ros::init(argc, argv, "box_object_detector");
//   BoxObjectDetector detector;
//   ros::spin();
//   return 0;
// }




















































#include <ros/ros.h>
#include <sensor_msgs/PointCloud2.h>
#include <geometry_msgs/PointStamped.h>
#include <trajectory_msgs/JointTrajectory.h>
#include <tf/transform_listener.h>
#include <tf/transform_broadcaster.h>

// PCL includes
#include <pcl_conversions/pcl_conversions.h>
#include <pcl/point_cloud.h>
#include <pcl/point_types.h>
#include <pcl/filters/passthrough.h>
#include <pcl/filters/crop_box.h>
#include <pcl/common/centroid.h>
#include <pcl/common/common.h>
#include <pcl/sample_consensus/method_types.h>
#include <pcl/sample_consensus/model_types.h>
#include <pcl/segmentation/sac_segmentation.h>
#include <pcl/filters/extract_indices.h>
#include <pcl/segmentation/extract_clusters.h>
#include <pcl_ros/transforms.h>
#include <Eigen/Dense>

typedef pcl::PointXYZ PointT;
typedef pcl::PointCloud<PointT> PointCloud;

class BoxObjectDetector
{
private:
  ros::NodeHandle nh_;
  ros::Subscriber pc_sub_;
  
  // Separate Target Publishers
  ros::Publisher grasp_target_pub_;
  ros::Publisher drop_target_pub_;
  
  // Separate PointCloud Publishers
  ros::Publisher clothes_pc_pub_;
  ros::Publisher dest_floor_pc_pub_;

  // Head controller publisher and timer
  ros::Publisher head_pub_;
  ros::Timer head_timer_;

  tf::TransformListener tf_listener_;
  tf::TransformBroadcaster tf_broadcaster_;

  // ROS Parameters
  double workspace_x_min_;
  double workspace_x_max_;
  double workspace_y_min_;
  double workspace_y_max_;
  double workspace_z_min_;
  double workspace_z_max_;

  double table_distance_threshold_;

  double cluster_tolerance_;
  int min_cluster_size_;
  int max_cluster_size_;

  double wall_margin_;
  double clothes_float_height_;
  double box_max_height_;

public:
  BoxObjectDetector()
  {
    // Load parameters from the ROS parameter server (private namespace)
    ros::NodeHandle private_nh("~");
    private_nh.param<double>("workspace_x_min", workspace_x_min_, 0.5);
    private_nh.param<double>("workspace_x_max", workspace_x_max_, 1.8);
    private_nh.param<double>("workspace_y_min", workspace_y_min_, -0.8);
    private_nh.param<double>("workspace_y_max", workspace_y_max_, 0.8);
    private_nh.param<double>("workspace_z_min", workspace_z_min_, 0.3);
    private_nh.param<double>("workspace_z_max", workspace_z_max_, 1.2);

    private_nh.param<double>("table_distance_threshold", table_distance_threshold_, 0.02);

    private_nh.param<double>("cluster_tolerance", cluster_tolerance_, 0.08);
    private_nh.param<int>("min_cluster_size", min_cluster_size_, 50);
    private_nh.param<int>("max_cluster_size", max_cluster_size_, 10000);

    private_nh.param<double>("wall_margin", wall_margin_, 0.03);
    private_nh.param<double>("clothes_float_height", clothes_float_height_, 0.02);
    private_nh.param<double>("box_max_height", box_max_height_, 0.40);

    // Subscribe to point cloud
    pc_sub_ = nh_.subscribe("/xtion/depth_registered/points", 1, &BoxObjectDetector::pointCloudCallback, this);

    // Target Publishers
    grasp_target_pub_ = nh_.advertise<geometry_msgs::PointStamped>("/tiago_vision/clothes_grasp_target", 1);
    drop_target_pub_ = nh_.advertise<geometry_msgs::PointStamped>("/tiago_vision/clothes_drop_target", 1);
    
    // PointCloud Publishers for RViz
    clothes_pc_pub_ = nh_.advertise<sensor_msgs::PointCloud2>("/tiago_vision/clothes_cloud", 1);
    dest_floor_pc_pub_ = nh_.advertise<sensor_msgs::PointCloud2>("/tiago_vision/destination_floor_cloud", 1);

    // Head controller command publisher and timer to automatically look down at startup
    //head_pub_ = nh_.advertise<trajectory_msgs::JointTrajectory>("/head_controller/command", 1);
    //head_timer_ = nh_.createTimer(ros::Duration(2.0), &BoxObjectDetector::tiltHeadCallback, this, true);

    ROS_INFO("BoxObjectDetector node initialized.");
  }

  void tiltHeadCallback(const ros::TimerEvent&)
  {
    trajectory_msgs::JointTrajectory traj;
    traj.joint_names.push_back("head_1_joint");
    traj.joint_names.push_back("head_2_joint");
    
    trajectory_msgs::JointTrajectoryPoint point;
    point.positions.push_back(0.0);
    point.positions.push_back(-0.6); // Tilt head downwards to face the tables
    point.velocities.push_back(0.0);
    point.velocities.push_back(0.0);
    point.time_from_start = ros::Duration(1.5);
    
    traj.points.push_back(point);
    head_pub_.publish(traj);
    ROS_INFO("Sent head controller command to tilt head downwards.");
  }

  void pointCloudCallback(const sensor_msgs::PointCloud2ConstPtr& msg)
  {
    // 1. Transform incoming PointCloud to base_footprint frame using latest transform (ros::Time(0))
    std::string target_frame = "base_footprint";
    sensor_msgs::PointCloud2 cloud_transformed_msg;
    try
    {
      if (!tf_listener_.waitForTransform(target_frame, msg->header.frame_id, ros::Time(0), ros::Duration(1.0)))
      {
        ROS_WARN_THROTTLE(5, "Timed out waiting for transform to %s", target_frame.c_str());
        return;
      }
      
      // Override message stamp to ros::Time(0) to bypass lag/extrapolation issues
      sensor_msgs::PointCloud2 msg_latest = *msg;
      msg_latest.header.stamp = ros::Time(0);
      
      if (!pcl_ros::transformPointCloud(target_frame, msg_latest, cloud_transformed_msg, tf_listener_))
      {
        ROS_WARN_THROTTLE(5, "Failed to transform point cloud to %s frame", target_frame.c_str());
        return;
      }
    }
    catch (tf::TransformException& ex)
    {
      ROS_WARN_THROTTLE(5, "TF exception in pointCloudCallback: %s", ex.what());
      return;
    }

    // Convert to PCL PointCloud
    PointCloud::Ptr cloud(new PointCloud);
    pcl::fromROSMsg(cloud_transformed_msg, *cloud);

    if (cloud->empty()) return;

    // 2. Passthrough Filter to crop the workspace of interest
    PointCloud::Ptr cropped_cloud(new PointCloud);
    pcl::CropBox<PointT> workspace_crop;
    workspace_crop.setInputCloud(cloud);
    workspace_crop.setMin(Eigen::Vector4f(workspace_x_min_, workspace_y_min_, workspace_z_min_, 1.0));
    workspace_crop.setMax(Eigen::Vector4f(workspace_x_max_, workspace_y_max_, workspace_z_max_, 1.0));
    workspace_crop.filter(*cropped_cloud);

    if (cropped_cloud->empty())
    {
      ROS_WARN_THROTTLE(5, "Workspace cropped cloud is empty. Check camera orientation and field of view.");
      return;
    }

    ROS_INFO_THROTTLE(10, "Cropped workspace cloud has %zu points", cropped_cloud->size());

    // 3. Segment the table plane
    pcl::ModelCoefficients::Ptr coefficients(new pcl::ModelCoefficients);
    pcl::PointIndices::Ptr inliers(new pcl::PointIndices);

    pcl::SACSegmentation<PointT> seg;
    seg.setOptimizeCoefficients(true);
    seg.setModelType(pcl::SACMODEL_PLANE);
    seg.setMethodType(pcl::SAC_RANSAC);
    seg.setMaxIterations(200);
    seg.setDistanceThreshold(table_distance_threshold_);

    seg.setInputCloud(cropped_cloud);
    seg.segment(*inliers, *coefficients);

    if (inliers->indices.empty())
    {
      ROS_WARN_THROTTLE(5, "Could not estimate table plane.");
      return;
    }

    // Check if the plane is horizontal (normal vector Z component should be close to 1 or -1)
    double z_normal = std::abs(coefficients->values[2]);
    if (z_normal < 0.8)
    {
      ROS_WARN_THROTTLE(5, "Plane detected is not horizontal (normal z = %.2f). Skipping plane removal.", z_normal);
      return;
    }

    // Extract non-planar points (objects sitting on the table)
    PointCloud::Ptr table_objects(new PointCloud);
    pcl::ExtractIndices<PointT> extract_table;
    extract_table.setInputCloud(cropped_cloud);
    extract_table.setIndices(inliers);
    extract_table.setNegative(true); // Remove the table plane
    extract_table.filter(*table_objects);

    if (table_objects->empty())
    {
      ROS_WARN_THROTTLE(5, "No objects remaining above the table.");
      return;
    }

    // Apply the plane-aligned coordinate transformation to filter out table-relative heights
    if (!coefficients->values.empty())
    {
      Eigen::Vector3f n(coefficients->values[0], coefficients->values[1], coefficients->values[2]);
      double d = coefficients->values[3];

      Eigen::Quaternionf Q_plane_base = Eigen::Quaternionf::FromTwoVectors(Eigen::Vector3f(0, 0, 1), n);
      Eigen::Vector3f t_plane_base = -d * n;

      Eigen::Affine3f T_plane_base = Eigen::Affine3f::Identity();
      T_plane_base.rotate(Q_plane_base.toRotationMatrix());
      T_plane_base.translate(t_plane_base);

      PointCloud::Ptr transf_cloud(new PointCloud);
      pcl::transformPointCloud(*table_objects, *transf_cloud, T_plane_base.inverse());

      PointCloud::Ptr filtered_cloud(new PointCloud);
      pcl::PassThrough<PointT> pass;
      pass.setInputCloud(transf_cloud);
      pass.setFilterFieldName("z");
      pass.setFilterLimits(0.01, 0.50); // Keep points between 1cm and 50cm above table top surface
      pass.filter(*filtered_cloud);

      // Transform back to the base frame
      table_objects->clear();
      pcl::transformPointCloud(*filtered_cloud, *table_objects, T_plane_base);
    }

    if (table_objects->empty())
    {
      ROS_WARN_THROTTLE(5, "No points remaining after table-aligned height filtering.");
      return;
    }

    ROS_INFO_THROTTLE(10, "Table objects cloud has %zu points", table_objects->size());

    // 4. Euclidean Cluster Extraction to separate the boxes
    pcl::search::KdTree<PointT>::Ptr tree(new pcl::search::KdTree<PointT>);
    tree->setInputCloud(table_objects);

    std::vector<pcl::PointIndices> cluster_indices;
    pcl::EuclideanClusterExtraction<PointT> ec;
    ec.setClusterTolerance(cluster_tolerance_);
    ec.setMinClusterSize(min_cluster_size_);
    ec.setMaxClusterSize(max_cluster_size_);
    ec.setSearchMethod(tree);
    ec.setInputCloud(table_objects);
    ec.extract(cluster_indices);

    if (cluster_indices.empty())
    {
      ROS_WARN_THROTTLE(5, "No object clusters detected on the table.");
      return;
    }

    ROS_INFO_THROTTLE(10, "Detected %zu clusters on the table.", cluster_indices.size());

    for (size_t c = 0; c < cluster_indices.size(); ++c)
    {
      const auto& indices = cluster_indices[c];
      
      // Extract cluster cloud
      PointCloud::Ptr cluster_cloud(new PointCloud);
      cluster_cloud->header = table_objects->header;
      for (const auto& idx : indices.indices)
      {
        cluster_cloud->points.push_back(table_objects->points[idx]);
      }

      // Compute centroid of the cluster in base_footprint frame
      Eigen::Vector4f cluster_centroid;
      pcl::compute3DCentroid(*cluster_cloud, cluster_centroid);

      ROS_INFO_THROTTLE(10, "Cluster %zu size: %zu points, Centroid: [%.3f, %.3f, %.3f]", 
                        c, cluster_cloud->size(), cluster_centroid[0], cluster_centroid[1], cluster_centroid[2]);

      // Lookup transform from base_footprint to odom to get robust world-relative Y position
      std::string cluster_class = "laundry basket";
      try
      {
        tf::StampedTransform tf_base_to_odom;
        tf_listener_.lookupTransform("odom", "base_footprint", ros::Time(0), tf_base_to_odom);
        tf::Vector3 centroid_base(cluster_centroid[0], cluster_centroid[1], cluster_centroid[2]);
        tf::Vector3 centroid_odom = tf_base_to_odom * centroid_base;
        
        // Midpoint between Box A (Y~0.54) and Box B (Y~-0.36) in odom frame is 0.09
        cluster_class = (centroid_odom.y() > 0.09) ? "washing machine box" : "laundry basket";
      }
      catch (tf::TransformException& ex)
      {
        ROS_WARN_THROTTLE(5, "Could not lookup transform to classify clusters in odom frame: %s. Falling back to base_footprint Y coordinate.", ex.what());
        cluster_class = (cluster_centroid[1] > 0.0) ? "washing machine box" : "laundry basket";
      }

      // 5. Segment floor plane of the box
      pcl::ModelCoefficients::Ptr box_floor_coefficients(new pcl::ModelCoefficients);
      pcl::PointIndices::Ptr box_floor_inliers(new pcl::PointIndices);

      pcl::SACSegmentation<PointT> box_seg;
      box_seg.setOptimizeCoefficients(true);
      
      // Force RANSAC to only find horizontal planes (the floor), ignoring vertical walls
      box_seg.setModelType(pcl::SACMODEL_PARALLEL_PLANE);
      box_seg.setAxis(Eigen::Vector3f(0, 0, 1));
      box_seg.setEpsAngle(0.2); // Allow ~11 degrees of tilt tolerance

      box_seg.setMethodType(pcl::SAC_RANSAC);
      box_seg.setMaxIterations(100);
      box_seg.setDistanceThreshold(0.02);

      box_seg.setInputCloud(cluster_cloud);
      box_seg.segment(*box_floor_inliers, *box_floor_coefficients);

      if (box_floor_inliers->indices.empty())
      {
        ROS_WARN("Could not find bottom plane for cluster '%s'.", cluster_class.c_str());
        continue;
      }

      // Extract floor cloud
      PointCloud::Ptr floor_cloud(new PointCloud);
      pcl::ExtractIndices<PointT> extract_floor;
      extract_floor.setInputCloud(cluster_cloud);
      extract_floor.setIndices(box_floor_inliers);
      extract_floor.setNegative(false); // Keep floor
      extract_floor.filter(*floor_cloud);

      if (floor_cloud->empty()) continue;

      if (cluster_class == "washing machine box")
      {
        // 6a. PCA-based Oriented Bounding Box (OBB) Crop logic
        Eigen::Vector4f floor_centroid;
        pcl::compute3DCentroid(*floor_cloud, floor_centroid);

        Eigen::Matrix3f covariance_matrix;
        pcl::computeCovarianceMatrixNormalized(*floor_cloud, floor_centroid, covariance_matrix);

        Eigen::SelfAdjointEigenSolver<Eigen::Matrix3f> eigen_solver(covariance_matrix, Eigen::ComputeEigenvectors);
        Eigen::Matrix3f eigenvectors = eigen_solver.eigenvectors();

        // Establish rotation directions (X: primary variance, Y: secondary variance, Z: plane normal)
        Eigen::Matrix3f rotation;
        rotation.col(0) = eigenvectors.col(2); // Local X along largest variance
        rotation.col(1) = eigenvectors.col(1); // Local Y along second largest variance
        rotation.col(2) = eigenvectors.col(0); // Local Z along plane normal
        // Ensure right-handed coordinate system
        // Force the local Z-axis to point UP (align with global +Z)
        if (rotation.col(2).dot(Eigen::Vector3f(0, 0, 1)) < 0)
        {
            rotation.col(2) = -rotation.col(2);
        }
        // Ensure right-handed coordinate system after potential Z-flip
        rotation.col(1) = rotation.col(2).cross(rotation.col(0));

        // Create the transform from box's local coordinate frame to base_footprint
        Eigen::Affine3f T_box_base = Eigen::Affine3f::Identity();
        T_box_base.rotate(rotation);
        T_box_base.translation() = floor_centroid.head<3>();

        // Transform cluster and floor to local box coordinate system
        PointCloud::Ptr cluster_local(new PointCloud);
        PointCloud::Ptr floor_local(new PointCloud);
        pcl::transformPointCloud(*cluster_cloud, *cluster_local, T_box_base.inverse());
        pcl::transformPointCloud(*floor_cloud, *floor_local, T_box_base.inverse());

        // Perform AABB on local floor cloud to obtain perfectly oriented dimensions
        PointT min_pt, max_pt;
        pcl::getMinMax3D(*floor_local, min_pt, max_pt);

        // Crop the clothes in box's local coordinates
        pcl::CropBox<PointT> clothes_crop;
        clothes_crop.setInputCloud(cluster_local);
        clothes_crop.setMin(Eigen::Vector4f(min_pt.x + wall_margin_, min_pt.y + wall_margin_, min_pt.z + clothes_float_height_, 1.0));
        clothes_crop.setMax(Eigen::Vector4f(max_pt.x - wall_margin_, max_pt.y - wall_margin_, min_pt.z + box_max_height_, 1.0));

        PointCloud::Ptr clothes_local(new PointCloud);
        clothes_crop.filter(*clothes_local);

        if (clothes_local->empty())
        {
          ROS_WARN_THROTTLE(5, "Clothes cloud is empty inside the washing machine box.");
          continue;
        }

        // Transform cropped clothes back to base_footprint frame
        PointCloud::Ptr clothes_cloud(new PointCloud);
        pcl::transformPointCloud(*clothes_local, *clothes_cloud, T_box_base);

        // Compute centroid in base_footprint
        Eigen::Vector4f clothes_centroid;
        pcl::compute3DCentroid(*clothes_cloud, clothes_centroid);

        // Publish target in base_footprint
        geometry_msgs::PointStamped centroid_msg;
        centroid_msg.header.frame_id = target_frame;
        centroid_msg.header.stamp = ros::Time::now();
        centroid_msg.point.x = floor_centroid[0];
        centroid_msg.point.y = floor_centroid[1];
        centroid_msg.point.z = floor_centroid[2] + 0.03; // Raise target above the floor for grasping
        grasp_target_pub_.publish(centroid_msg);

        // Broadcast TF transform relative to base_footprint
        tf::Transform transform;
        transform.setOrigin(tf::Vector3(floor_centroid[0], floor_centroid[1], floor_centroid[2] + 0.15)); // Raise target above the floor for grasping
        transform.setRotation(tf::Quaternion(0, 0, 0, 1));
        tf_broadcaster_.sendTransform(tf::StampedTransform(transform, ros::Time::now(), target_frame, "clothes_grasp_target"));

        // Publish clothes point cloud in base_footprint
        sensor_msgs::PointCloud2 clothes_pc_msg;
        pcl::toROSMsg(*clothes_cloud, clothes_pc_msg);
        clothes_pc_msg.header.frame_id = target_frame;
        clothes_pc_msg.header.stamp = ros::Time::now(); 
        clothes_pc_pub_.publish(clothes_pc_msg);

        ROS_INFO_THROTTLE(2, "Detected clothes grasp target: [%.3f, %.3f, %.3f] in base_footprint", 
                          floor_centroid[0], floor_centroid[1], floor_centroid[2]);
      }
      else if (cluster_class == "laundry basket")
      {
        // 6b. Floor centroid is the destination target in base_footprint
        Eigen::Vector4f floor_centroid;
        pcl::compute3DCentroid(*floor_cloud, floor_centroid);

        // Publish target in base_footprint
        geometry_msgs::PointStamped centroid_msg;
        centroid_msg.header.frame_id = target_frame;
        centroid_msg.header.stamp = ros::Time::now();
        centroid_msg.point.x = floor_centroid[0];
        centroid_msg.point.y = floor_centroid[1];
        centroid_msg.point.z = floor_centroid[2];
        drop_target_pub_.publish(centroid_msg);

        // Broadcast TF transform relative to base_footprint
        tf::Transform transform;
        transform.setOrigin(tf::Vector3(floor_centroid[0], floor_centroid[1], floor_centroid[2]));
        transform.setRotation(tf::Quaternion(0, 0, 0, 1));
        tf_broadcaster_.sendTransform(tf::StampedTransform(transform, ros::Time::now(), target_frame, "clothes_drop_target"));

        // Publish Floor PointCloud in base_footprint
        sensor_msgs::PointCloud2 floor_pc_msg;
        pcl::toROSMsg(*floor_cloud, floor_pc_msg);
        floor_pc_msg.header.frame_id = target_frame;
        floor_pc_msg.header.stamp = ros::Time::now();
        dest_floor_pc_pub_.publish(floor_pc_msg);

        ROS_INFO_THROTTLE(2, "Detected clothes drop target: [%.3f, %.3f, %.3f] in base_footprint", 
                          floor_centroid[0], floor_centroid[1], floor_centroid[2]);
      }
    }
  }
};

int main(int argc, char** argv)
{
  ros::init(argc, argv, "box_object_detector");
  BoxObjectDetector detector;
  ros::spin();
  return 0;
}