//#include <ros/ros.h>
//#include <sensor_msgs/PointCloud2.h>
//#include <geometry_msgs/PointStamped.h>
//#include <trajectory_msgs/JointTrajectory.h>
//#include <tf/transform_listener.h>
//#include <tf/transform_broadcaster.h>
//
//// PCL includes
//#include <pcl_conversions/pcl_conversions.h>
//#include <pcl/point_cloud.h>
//#include <pcl/point_types.h>
//#include <pcl/filters/passthrough.h>
//#include <pcl/filters/crop_box.h>
//#include <pcl/common/centroid.h>
//#include <pcl/common/common.h>
//#include <pcl/sample_consensus/method_types.h>
//#include <pcl/sample_consensus/model_types.h>
//#include <pcl/sample_consensus/sac_model_plane.h>
//#include <pcl/segmentation/sac_segmentation.h>
//#include <pcl/filters/extract_indices.h>
//#include <pcl/segmentation/extract_clusters.h>
//#include <pcl_ros/transforms.h>
//#include <Eigen/Dense>
//#include <Eigen/Geometry>
//#include <pcl/filters/voxel_grid.h>
//
//typedef pcl::PointXYZ PointT;
//typedef pcl::PointCloud<PointT> PointCloud;
//
//class BoxObjectDetector
//{
//private:
//  ros::NodeHandle nh_;
//  ros::Subscriber pc_sub_;
//  
//  ros::Publisher box_a_pub_; // Navigation TF for Box A
//  ros::Publisher box_b_pub_; // Navigation TF for Box B
//  ros::Publisher grasp_target_pub_; // Manipulation TF for Clothes
//  ros::Publisher drop_target_pub_;  // Manipulation TF for Drop
//  
//  ros::Publisher clothes_pc_pub_;
//  ros::Publisher dest_floor_pc_pub_;
//
//  tf::TransformListener tf_listener_;
//  tf::TransformBroadcaster tf_broadcaster_;
//
//  double workspace_x_min_, workspace_x_max_;
//  double workspace_y_min_, workspace_y_max_;
//  double workspace_z_min_, workspace_z_max_;
//  double table_distance_threshold_;
//  double cluster_tolerance_;
//  int min_cluster_size_, max_cluster_size_;
//
//  // Memory states for BOTH boxes independently
//  pcl::ModelCoefficients::Ptr last_floor_coeffs_a_;
//  bool has_valid_floor_memory_a_ = false;
//  pcl::ModelCoefficients::Ptr last_floor_coeffs_b_;
//  bool has_valid_floor_memory_b_ = false;
//
//  enum TrackerState { INITIALIZING, LOCKED };
//  TrackerState state_a_ = INITIALIZING;
//  int frame_count_a_ = 0;
//  const int INITIALIZATION_FRAMES = 30;
//
//  Eigen::Vector3f sum_centroid_a_ = Eigen::Vector3f::Zero();
//  Eigen::Vector3f sum_z_axis_a_ = Eigen::Vector3f::Zero();
//  Eigen::Vector3f sum_x_axis_a_ = Eigen::Vector3f::Zero();
//
//  Eigen::Matrix4f locked_transform_a_ = Eigen::Matrix4f::Identity();
//  Eigen::Vector4f locked_centroid_a_ = Eigen::Vector4f::Zero();
//
//  Eigen::Vector3f smoothed_clothes_centroid_ = Eigen::Vector3f::Zero(); // memory for the EMA Filter
//
//  PointT locked_min_pt_a_;
//  PointT locked_max_pt_a_;
//
//public:
//  BoxObjectDetector()
//  {
//    ros::NodeHandle private_nh("~");
//    private_nh.param<double>("workspace_x_min", workspace_x_min_, 0.5);
//    private_nh.param<double>("workspace_x_max", workspace_x_max_, 1.8);
//    private_nh.param<double>("workspace_y_min", workspace_y_min_, -0.8);
//    private_nh.param<double>("workspace_y_max", workspace_y_max_, 0.8);
//    private_nh.param<double>("workspace_z_min", workspace_z_min_, 0.3);
//    private_nh.param<double>("workspace_z_max", workspace_z_max_, 1.2);
//    private_nh.param<double>("table_distance_threshold", table_distance_threshold_, 0.02);
//    private_nh.param<double>("cluster_tolerance", cluster_tolerance_, 0.08);
//    private_nh.param<int>("min_cluster_size", min_cluster_size_, 50);
//    private_nh.param<int>("max_cluster_size", max_cluster_size_, 10000);
//
//    std::string point_cloud_topic;
//    private_nh.param<std::string>("point_cloud_topic", point_cloud_topic, "/xtion/depth_registered/points");
//    pc_sub_ = nh_.subscribe(point_cloud_topic, 1, &BoxObjectDetector::pointCloudCallback, this);
//
//    box_a_pub_ = nh_.advertise<geometry_msgs::PointStamped>("/tiago_vision/box_a_center", 1);
//    box_b_pub_ = nh_.advertise<geometry_msgs::PointStamped>("/tiago_vision/box_b_center", 1);
//    
//    grasp_target_pub_ = nh_.advertise<geometry_msgs::PointStamped>("/tiago_vision/clothes_grasp_target", 1);
//    drop_target_pub_ = nh_.advertise<geometry_msgs::PointStamped>("/tiago_vision/clothes_drop_target", 1);
//    
//    clothes_pc_pub_ = nh_.advertise<sensor_msgs::PointCloud2>("/tiago_vision/clothes_cloud", 1);
//    dest_floor_pc_pub_ = nh_.advertise<sensor_msgs::PointCloud2>("/tiago_vision/destination_floor_cloud", 1);
//
//    ROS_INFO("BoxObjectDetector (Dual Tracker Architecture) node initialized.");
//  }
//
//  void pointCloudCallback(const sensor_msgs::PointCloud2ConstPtr& msg)
//  {
//    std::string target_frame = "base_footprint";
//    sensor_msgs::PointCloud2 cloud_transformed_msg;
//    try
//    {
//      if (!tf_listener_.waitForTransform(target_frame, msg->header.frame_id, ros::Time(0), ros::Duration(1.0))) return;
//      sensor_msgs::PointCloud2 msg_latest = *msg;
//      msg_latest.header.stamp = ros::Time(0);
//      pcl_ros::transformPointCloud(target_frame, msg_latest, cloud_transformed_msg, tf_listener_);
//    }
//    catch (tf::TransformException& ex) { return; }
//
//    PointCloud::Ptr cloud(new PointCloud);
//    pcl::fromROSMsg(cloud_transformed_msg, *cloud);
//    if (cloud->empty()) return;
//
//    // --- Step 0: Workspace Crop & Decapitation Filter ---
//    PointCloud::Ptr cropped_cloud(new PointCloud);
//    pcl::CropBox<PointT> workspace_crop;
//    workspace_crop.setInputCloud(cloud);
//    workspace_crop.setMin(Eigen::Vector4f(workspace_x_min_, workspace_y_min_, workspace_z_min_, 1.0));
//    workspace_crop.setMax(Eigen::Vector4f(workspace_x_max_, workspace_y_max_, workspace_z_max_, 1.0));
//    workspace_crop.filter(*cropped_cloud);
//
//    pcl::PassThrough<PointT> z_filter;
//    z_filter.setInputCloud(cropped_cloud);
//    z_filter.setFilterFieldName("z");
//    z_filter.setFilterLimits(0.40, 1.00); 
//    z_filter.filter(*cropped_cloud);
//
//    PointCloud::Ptr downsampled_cloud(new PointCloud);
//    pcl::VoxelGrid<PointT> vg;
//    vg.setInputCloud(cropped_cloud);
//    vg.setLeafSize(0.005f, 0.005f, 0.005f); // 5 mm voxel
//    vg.filter(*downsampled_cloud);
//
//    if (downsampled_cloud->empty()) return;
//
//    // ======================================================================
//    // Split the world in half using the stable `odom` frame to track both boxes
//    // ======================================================================
//    PointCloud::Ptr cloud_a(new PointCloud); // Left side (Washing Machine)
//    PointCloud::Ptr cloud_b(new PointCloud); // Right side (Laundry Basket)
//
//    tf::StampedTransform tf_base_to_odom;
//    bool has_odom = true;
//    try {
//        tf_listener_.lookupTransform("odom", target_frame, ros::Time(0), tf_base_to_odom);
//    } catch (tf::TransformException& ex) {
//        has_odom = false;
//    }
//
//    for (const auto& pt : downsampled_cloud->points) {
//        if (has_odom) {
//            tf::Vector3 pt_base(pt.x, pt.y, pt.z);
//            tf::Vector3 pt_odom = tf_base_to_odom * pt_base;
//            if (pt_odom.y() > 0.05) cloud_a->points.push_back(pt);
//            else cloud_b->points.push_back(pt);
//        } else {
//            // Fallback
//            if (pt.y > 0.0) cloud_a->points.push_back(pt);
//            else cloud_b->points.push_back(pt);
//        }
//    }
//    cloud_a->width = cloud_a->points.size(); cloud_a->height = 1;
//    cloud_b->width = cloud_b->points.size(); cloud_b->height = 1;
//
//    // ======================================================================
//    // DUAL TRACKER LOOP: Process Box A, then Box B independently
//    // ======================================================================
//    for (int box_idx = 0; box_idx < 2; ++box_idx) 
//    {
//        PointCloud::Ptr current_cloud = (box_idx == 0) ? cloud_a : cloud_b;
//        bool is_washing_machine = (box_idx == 0);
//
//        if (current_cloud->empty() || current_cloud->points.size() < 100) continue;
//
//        // --- Step 1 & 2: The Smart Two-Plane Extractor ---
//        pcl::SACSegmentation<PointT> seg;
//        seg.setOptimizeCoefficients(true);
//        seg.setModelType(pcl::SACMODEL_PARALLEL_PLANE);
//        seg.setAxis(Eigen::Vector3f(0, 0, 1));
//        seg.setEpsAngle(0.15); 
//        seg.setMethodType(pcl::SAC_RANSAC);
//        seg.setMaxIterations(200);
//        seg.setDistanceThreshold(0.02);
//
//        pcl::ModelCoefficients::Ptr plane1_coeffs(new pcl::ModelCoefficients);
//        pcl::PointIndices::Ptr plane1_inliers(new pcl::PointIndices);
//        pcl::ModelCoefficients::Ptr table_coeffs(new pcl::ModelCoefficients);
//        pcl::PointIndices::Ptr table_inliers(new pcl::PointIndices);
//        seg.setInputCloud(current_cloud);
//        //seg.segment(*plane1_inliers, *plane1_coeffs);
//        seg.segment(*table_inliers, *table_coeffs);
//
//        //if (plane1_inliers->indices.empty()) continue;
//        if (table_inliers->indices.empty()) {
//            ROS_WARN_THROTTLE(2.0, "[Vision] Failed to find table.");
//            continue;
//        }
//
//        float table_z = -table_coeffs->values[3] / table_coeffs->values[2];
//
//
//        PointCloud::Ptr remaining_cloud(new PointCloud);
//        //pcl::ExtractIndices<PointT> extract;
//        //extract.setInputCloud(current_cloud);
//        //extract.setIndices(plane1_inliers);
//        //extract.setNegative(true);
//        //extract.filter(*remaining_cloud);
//        pcl::PassThrough<PointT> pass_table;
//        pass_table.setInputCloud(current_cloud);
//        pass_table.setFilterFieldName("z");
//        pass_table.setFilterLimits(table_z + 0.02, 1.5); // 2cm above table to ignore table noise
//        PointCloud::Ptr above_table_cloud(new PointCloud);
//        pass_table.filter(*above_table_cloud);
//        if (above_table_cloud->points.size() < 50) {
//            ROS_WARN_THROTTLE(2.0, "[Vision] No objects found above table.");
//            continue;
//        }
//
//        // What remains is ONLY the box and the clothes. We use this for geometry!
//        PointCloud::Ptr floor_cloud = above_table_cloud; 
//        PointCloud::Ptr box_and_clothes = above_table_cloud;
//
//        Eigen::Vector4f pca_centroid;
//        pcl::compute3DCentroid(*above_table_cloud, pca_centroid);
//        
//        // FORCE the Z height to be exactly the table surface so it never jitters vertically
//        pca_centroid[2] = table_z;
//
//
//        //pcl::ModelCoefficients::Ptr plane2_coeffs(new pcl::ModelCoefficients);
//        //pcl::PointIndices::Ptr plane2_inliers(new pcl::PointIndices);
//        //seg.setInputCloud(remaining_cloud);
//        //seg.segment(*plane2_inliers, *plane2_coeffs);
////
//        //pcl::ModelCoefficients::Ptr active_floor_coeffs(new pcl::ModelCoefficients);
//        //PointCloud::Ptr box_and_clothes(new PointCloud);
//        //
//        //float z1 = -plane1_coeffs->values[3] / plane1_coeffs->values[2];
//        //
//        //if (!plane2_inliers->indices.empty() && plane2_inliers->indices.size() > 100) {
//        //    float z2 = -plane2_coeffs->values[3] / plane2_coeffs->values[2];
//        //    
//        //    if (z2 > z1 + 0.03) { 
//        //        active_floor_coeffs = plane2_coeffs;
//        //        box_and_clothes = remaining_cloud; 
//        //    } else if (z1 > z2 + 0.03) { 
//        //        active_floor_coeffs = plane1_coeffs;
//        //        extract.setInputCloud(current_cloud);
//        //        extract.setIndices(plane2_inliers);
//        //        extract.setNegative(true);
//        //        extract.filter(*box_and_clothes); 
//        //    } else {
//        //        active_floor_coeffs = plane1_coeffs;
//        //        box_and_clothes = remaining_cloud;
//        //    }
//        //} else {
//        //    active_floor_coeffs = plane1_coeffs;
//        //    box_and_clothes = remaining_cloud; 
//        //}
//        //
//        //// Independent Memory Updates
//        //if (is_washing_machine) {
//        //    last_floor_coeffs_a_ = active_floor_coeffs;
//        //    has_valid_floor_memory_a_ = true;
//        //} else {
//        //    last_floor_coeffs_b_ = active_floor_coeffs;
//        //    has_valid_floor_memory_b_ = true;
//        //}
////
//        //// --- Box Detector Core ---
//        //pcl::SampleConsensusModelPlane<PointT>::Ptr plane_model(new pcl::SampleConsensusModelPlane<PointT>(box_and_clothes));
//        //std::vector<int> active_floor_inliers;
//        //
//        //Eigen::VectorXf eigen_coeffs(active_floor_coeffs->values.size());
//        //for (size_t i = 0; i < active_floor_coeffs->values.size(); ++i) {
//        //    eigen_coeffs[i] = active_floor_coeffs->values[i];
//        //}
//        //
//        //plane_model->selectWithinDistance(eigen_coeffs, 0.015, active_floor_inliers);
////
//        //if (active_floor_inliers.empty()) {
//        //    ROS_WARN_THROTTLE(2.0, "[Vision] Failed to extract floor points.");
//        //    continue;
//        //}
////
//        //PointCloud::Ptr floor_cloud(new PointCloud);
//        //pcl::copyPointCloud(*box_and_clothes, active_floor_inliers, *floor_cloud);
////
//        //Eigen::Vector4f pca_centroid;
//        //pcl::compute3DCentroid(*floor_cloud, pca_centroid);
////
//        // ======================================================================
//        // OUTPUT 1: PUBLISH THIS BOX'S TARGET 
//        // ======================================================================
//
//        if (is_washing_machine) {
//            // ONLY publish the Box A TF if we have achieved a locked state
//            if (state_a_ == LOCKED) {
//                geometry_msgs::PointStamped box_msg;
//                box_msg.header.frame_id = target_frame;
//                box_msg.header.stamp = ros::Time::now();
//                box_msg.point.x = locked_centroid_a_[0];
//                box_msg.point.y = locked_centroid_a_[1];
//                box_msg.point.z = locked_centroid_a_[2];
//                box_a_pub_.publish(box_msg);
//
//                tf::Transform transform;
//                transform.setOrigin(tf::Vector3(locked_centroid_a_[0], locked_centroid_a_[1], locked_centroid_a_[2]));
//                
//                // Lock the orientation using the calculated orthogonal axes
//                Eigen::Quaternionf q(locked_transform_a_.block<3,3>(0,0));
//                transform.setRotation(tf::Quaternion(q.x(), q.y(), q.z(), q.w()));
//                
//                tf_broadcaster_.sendTransform(tf::StampedTransform(transform, ros::Time::now(), target_frame, "box_a_center"));
//            }
//        } else {
//            // Box B logic remains unchanged
//            geometry_msgs::PointStamped box_msg;
//            box_msg.header.frame_id = target_frame;
//            box_msg.header.stamp = ros::Time::now();
//            box_msg.point.x = pca_centroid[0];
//            box_msg.point.y = pca_centroid[1];
//            box_msg.point.z = pca_centroid[2];
//            
//            box_b_pub_.publish(box_msg);
//            tf::Transform transform;
//            transform.setOrigin(tf::Vector3(pca_centroid[0], pca_centroid[1], pca_centroid[2]));
//            transform.setRotation(tf::Quaternion(0, 0, 0, 1));
//            tf_broadcaster_.sendTransform(tf::StampedTransform(transform, ros::Time::now(), target_frame, "box_b_center"));
//            
//            // Box B Drop Target
//            drop_target_pub_.publish(box_msg);
//            tf_broadcaster_.sendTransform(tf::StampedTransform(transform, ros::Time::now(), target_frame, "clothes_drop_target"));
//
//            sensor_msgs::PointCloud2 floor_pc_msg;
//            pcl::toROSMsg(*floor_cloud, floor_pc_msg);
//            floor_pc_msg.header.frame_id = target_frame;
//            floor_pc_msg.header.stamp = ros::Time::now();
//            dest_floor_pc_pub_.publish(floor_pc_msg);
//
//            continue; 
//        }
//
//        // ======================================================================
//        // CLOTHES DETECTOR CORE (Only runs if we are looking at Box A)
//        // ======================================================================
//        if (state_a_ == INITIALIZING) {
//            // 1. Run your existing PCA
//            Eigen::Matrix3f covariance;
//            pcl::computeCovarianceMatrixNormalized(*floor_cloud, pca_centroid, covariance);
//            Eigen::SelfAdjointEigenSolver<Eigen::Matrix3f> eigen_solver(covariance, Eigen::ComputeEigenvectors);
//            Eigen::Matrix3f eigen_vectors = eigen_solver.eigenvectors();
//
//            Eigen::Vector3f z_axis = eigen_vectors.col(0); 
//            Eigen::Vector3f x_axis = eigen_vectors.col(2); 
//            if (z_axis.dot(Eigen::Vector3f(0, 0, 1)) < 0) z_axis *= -1.0f;
//
//            z_axis.normalize();
//            x_axis.normalize();
//
//            // 2. Accumulate the vectors
//            sum_centroid_a_ += pca_centroid.head<3>();
//            sum_z_axis_a_ += z_axis;
//            sum_x_axis_a_ += x_axis;
//            frame_count_a_++;
//
//            ROS_INFO_THROTTLE(0.5, "[Vision] Initializing Box A Frame... (%d/%d)", frame_count_a_, INITIALIZATION_FRAMES);
//
//            // 3. Lock the frame once we hit the threshold
//            if (frame_count_a_ >= INITIALIZATION_FRAMES) {
//                Eigen::Vector3f avg_centroid = sum_centroid_a_ / INITIALIZATION_FRAMES;
//                
//                Eigen::Vector3f avg_z = sum_z_axis_a_.normalized();
//                Eigen::Vector3f avg_x = sum_x_axis_a_.normalized();
//
//                Eigen::Vector3f avg_y = avg_z.cross(avg_x).normalized();
//                avg_x = avg_y.cross(avg_z).normalized(); 
//
//                locked_transform_a_.block<1, 3>(0, 0) = avg_x.transpose();
//                locked_transform_a_.block<1, 3>(1, 0) = avg_y.transpose();
//                locked_transform_a_.block<1, 3>(2, 0) = avg_z.transpose();
//                locked_transform_a_.block<3, 1>(0, 3) = -1.0f * (locked_transform_a_.block<3, 3>(0, 0) * avg_centroid);
//                
//                //locked_centroid_a_ = Eigen::Vector4f(avg_centroid[0], avg_centroid[1], avg_centroid[2], 1.0f);
//
//                //state_a_ = LOCKED;
//                //ROS_INFO("[Vision] SUCCESS: Box A coordinate frame and bounding box LOCKED.");
//                locked_centroid_a_ = Eigen::Vector4f(avg_centroid[0], avg_centroid[1], avg_centroid[2], 1.0f);
//
//                // Calculate the physical boundaries based on the isolated Box/Clothes
//                PointCloud::Ptr local_floor(new PointCloud);
//                pcl::transformPointCloud(*floor_cloud, *local_floor, locked_transform_a_);
//                pcl::getMinMax3D(*local_floor, locked_min_pt_a_, locked_max_pt_a_);
//
//                // ==========================================================
//                // THE FIX: CLAMP THE BOUNDARIES TO PREVENT BLEED
//                // Forces the search area to a max of 40cm x 40cm around the center
//                // ==========================================================
//                float max_radius = 0.20f; 
//                locked_min_pt_a_.x = std::max(locked_min_pt_a_.x, -max_radius);
//                locked_max_pt_a_.x = std::min(locked_max_pt_a_.x,  max_radius);
//                locked_min_pt_a_.y = std::max(locked_min_pt_a_.y, -max_radius);
//                locked_max_pt_a_.y = std::min(locked_max_pt_a_.y,  max_radius);
//
//                state_a_ = LOCKED;
//                ROS_INFO("[Vision] SUCCESS: Box A coordinate frame and bounding box LOCKED.");
//            }
//
//            continue; // Skip clothes detection until locked
//        }
//        else if (state_a_ == LOCKED) {
//            // Apply the locked transformation directly to the existing box_and_clothes cloud
//            PointCloud::Ptr local_cloud(new PointCloud);
//            pcl::transformPointCloud(*box_and_clothes, *local_cloud, locked_transform_a_);
//
//            PointCloud::Ptr cropped_interior(new PointCloud);
//            pcl::PassThrough<PointT> pass;
//            
//            pass.setInputCloud(local_cloud);
//            pass.setFilterFieldName("x");
//            // Use the frozen limits!
//            pass.setFilterLimits(locked_min_pt_a_.x + 0.03, locked_max_pt_a_.x - 0.03);
//            pass.filter(*cropped_interior);
//
//            pass.setInputCloud(cropped_interior);
//            pass.setFilterFieldName("y");
//            // Use the frozen limits!
//            pass.setFilterLimits(locked_min_pt_a_.y + 0.03, locked_max_pt_a_.y - 0.03);
//            pass.filter(*cropped_interior);
//
//            pass.setInputCloud(cropped_interior);
//            pass.setFilterFieldName("z");
//            pass.setFilterLimits(0.02, 0.15);
//            pass.filter(*cropped_interior);
//
//            if (cropped_interior->empty()){
//                ROS_WARN_THROTTLE(2, "[Clothes Detector] Interior empty. Box TF is locked, waiting for clothes...");
//                continue;
//            } 
//
//            PointCloud::Ptr isolated_clothes(new PointCloud);
//            // Re-transform back to global space using the locked inverse!
//            pcl::transformPointCloud(*cropped_interior, *isolated_clothes, locked_transform_a_.inverse());
//
//            pcl::search::KdTree<PointT>::Ptr tree(new pcl::search::KdTree<PointT>);
//            tree->setInputCloud(isolated_clothes);
//            std::vector<pcl::PointIndices> cluster_indices;
//            pcl::EuclideanClusterExtraction<PointT> ec;
//            ec.setClusterTolerance(cluster_tolerance_);
//            ec.setMinClusterSize(min_cluster_size_);
//            ec.setMaxClusterSize(max_cluster_size_);
//            ec.setSearchMethod(tree);
//            ec.setInputCloud(isolated_clothes);
//            ec.extract(cluster_indices);
//
//            if (cluster_indices.empty()) {
//                ROS_WARN_THROTTLE(2, "[Clothes Detector] No clusters found. Box TF is locked, waiting for clothes...");
//                continue;
//            }
//            
//            size_t max_size = 0;
//            int largest_cluster_idx = 0;
//            for (size_t i = 0; i < cluster_indices.size(); ++i) {
//                if (cluster_indices[i].indices.size() > max_size) {
//                    max_size = cluster_indices[i].indices.size();
//                    largest_cluster_idx = i;
//                }
//            }
//
//            PointCloud::Ptr target_clothes(new PointCloud);
//            for (const auto& idx : cluster_indices[largest_cluster_idx].indices) {
//                target_clothes->points.push_back(isolated_clothes->points[idx]);
//            }
//
//            // ======================================================================
//            // OUTPUT 2: MANIPULATION GRASP TARGET (WITH EMA FILTER)
//            // ======================================================================
//
//            Eigen::Vector4f clothes_centroid;
//            pcl::compute3DCentroid(*target_clothes, clothes_centroid);
//
//            // EMA Smoothing Filter to kill the noise jitter
//            if (smoothed_clothes_centroid_.isZero()) {
//                smoothed_clothes_centroid_ = clothes_centroid.head<3>();
//            } else {
//                float alpha = 0.15f; // Smoothing factor (lower = smoother but slightly delayed)
//                smoothed_clothes_centroid_ = (alpha * clothes_centroid.head<3>()) + ((1.0f - alpha) * smoothed_clothes_centroid_);
//            }
//
//            geometry_msgs::PointStamped centroid_msg;
//            centroid_msg.header.frame_id = target_frame;
//            centroid_msg.header.stamp = ros::Time::now();
//            centroid_msg.point.x = smoothed_clothes_centroid_[0];
//            centroid_msg.point.y = smoothed_clothes_centroid_[1];
//            centroid_msg.point.z = locked_centroid_a_[2]; // Keep Z strictly locked
//
//            grasp_target_pub_.publish(centroid_msg);
//            tf::Transform transform;
//            transform.setOrigin(tf::Vector3(smoothed_clothes_centroid_[0], smoothed_clothes_centroid_[1], locked_centroid_a_[2]));
//            transform.setRotation(tf::Quaternion(0, 0, 0, 1));
//            tf_broadcaster_.sendTransform(tf::StampedTransform(transform, ros::Time::now(), target_frame, "clothes_grasp_target"));
//            
//            sensor_msgs::PointCloud2 clothes_pc_msg;
//            pcl::toROSMsg(*target_clothes, clothes_pc_msg);
//            clothes_pc_msg.header.frame_id = target_frame;
//            clothes_pc_msg.header.stamp = ros::Time::now();
//            clothes_pc_pub_.publish(clothes_pc_msg);
//
//            ROS_INFO_THROTTLE(2.0, "[Clothes Detector] Success. Publishing LOCKED and SMOOTHED grasp target.");
//        }
//    }
//  }
//};
//
//int main(int argc, char** argv)
//{
//  ros::init(argc, argv, "box_object_detector");
//  BoxObjectDetector detector;
//  ros::spin();
//  return 0;
//}



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
  ros::Publisher table_pc_pub_;
  ros::Publisher box_a_pc_pub_;
  ros::Publisher box_b_pc_pub_;
  ros::Publisher box_a_floor_pc_pub_;
  ros::Publisher box_b_floor_pc_pub_;

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
    table_pc_pub_ = nh_.advertise<sensor_msgs::PointCloud2>("/tiago_vision/table_cloud", 1);
    box_a_pc_pub_ = nh_.advertise<sensor_msgs::PointCloud2>("/tiago_vision/box_a_cloud", 1);
    box_b_pc_pub_ = nh_.advertise<sensor_msgs::PointCloud2>("/tiago_vision/box_b_cloud", 1);
    box_a_floor_pc_pub_ = nh_.advertise<sensor_msgs::PointCloud2>("/tiago_vision/box_a_floor_cloud", 1);
    box_b_floor_pc_pub_ = nh_.advertise<sensor_msgs::PointCloud2>("/tiago_vision/box_b_floor_cloud", 1);

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
    // 1. Transform incoming PointCloud to base_footprint frame at the cloud timestamp.
    // Keep this timestamp on all published detections so downstream nodes can reject
    // stale results after base motion.
    std::string target_frame = "base_footprint";
    ros::Time source_stamp = msg->header.stamp;
    if (source_stamp.isZero())
    {
      source_stamp = ros::Time::now();
    }

    sensor_msgs::PointCloud2 cloud_transformed_msg;
    try
    {
      if (!tf_listener_.waitForTransform(target_frame, msg->header.frame_id, source_stamp, ros::Duration(1.0)))
      {
        ROS_WARN_THROTTLE(5, "Timed out waiting for transform to %s", target_frame.c_str());
        return;
      }

      if (!pcl_ros::transformPointCloud(target_frame, *msg, cloud_transformed_msg, tf_listener_))
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

    // Extract the table plane for collision modeling, then remove it for object clustering.
    PointCloud::Ptr table_cloud(new PointCloud);
    pcl::ExtractIndices<PointT> extract_table;
    extract_table.setInputCloud(cropped_cloud);
    extract_table.setIndices(inliers);
    extract_table.setNegative(false); // Keep the table plane
    extract_table.filter(*table_cloud);

    if (!table_cloud->empty())
    {
      sensor_msgs::PointCloud2 table_pc_msg;
      pcl::toROSMsg(*table_cloud, table_pc_msg);
      table_pc_msg.header.frame_id = target_frame;
      table_pc_msg.header.stamp = source_stamp;
      table_pc_pub_.publish(table_pc_msg);
    }

    // Extract non-planar points (objects sitting on the table)
    PointCloud::Ptr table_objects(new PointCloud);
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
      cluster_cloud->width = cluster_cloud->points.size();
      cluster_cloud->height = 1;
      cluster_cloud->is_dense = false;

      // Compute centroid of the cluster in base_footprint frame
      Eigen::Vector4f cluster_centroid;
      pcl::compute3DCentroid(*cluster_cloud, cluster_centroid);

      ROS_INFO_THROTTLE(10, "Cluster %zu size: %zu points, Centroid: [%.3f, %.3f, %.3f]", 
                        c, cluster_cloud->size(), cluster_centroid[0], cluster_centroid[1], cluster_centroid[2]);

      std::string cluster_class = (cluster_centroid[1] > 0.0) ? "washing machine box" : "laundry basket";

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
        sensor_msgs::PointCloud2 box_a_pc_msg;
        pcl::toROSMsg(*cluster_cloud, box_a_pc_msg);
        box_a_pc_msg.header.frame_id = target_frame;
        box_a_pc_msg.header.stamp = source_stamp;
        box_a_pc_pub_.publish(box_a_pc_msg);

        sensor_msgs::PointCloud2 box_a_floor_pc_msg;
        pcl::toROSMsg(*floor_cloud, box_a_floor_pc_msg);
        box_a_floor_pc_msg.header.frame_id = target_frame;
        box_a_floor_pc_msg.header.stamp = source_stamp;
        box_a_floor_pc_pub_.publish(box_a_floor_pc_msg);

        Eigen::Vector4f floor_centroid;
        pcl::compute3DCentroid(*floor_cloud, floor_centroid);

        Eigen::Matrix3f covariance_matrix;
        pcl::computeCovarianceMatrixNormalized(*floor_cloud, floor_centroid, covariance_matrix);

        Eigen::SelfAdjointEigenSolver<Eigen::Matrix3f> eigen_solver(covariance_matrix, Eigen::ComputeEigenvectors);
        Eigen::Matrix3f eigenvectors = eigen_solver.eigenvectors();

        Eigen::Matrix3f rotation;
        rotation.col(0) = eigenvectors.col(2);
        rotation.col(1) = eigenvectors.col(1);
        rotation.col(2) = eigenvectors.col(0);
        if (rotation.col(2).dot(Eigen::Vector3f(0, 0, 1)) < 0)
        {
          rotation.col(2) = -rotation.col(2);
        }
        rotation.col(1) = rotation.col(2).cross(rotation.col(0));

        Eigen::Affine3f T_box_base = Eigen::Affine3f::Identity();
        T_box_base.rotate(rotation);
        T_box_base.translation() = floor_centroid.head<3>();

        PointCloud::Ptr cluster_local(new PointCloud);
        PointCloud::Ptr floor_local(new PointCloud);
        pcl::transformPointCloud(*cluster_cloud, *cluster_local, T_box_base.inverse());
        pcl::transformPointCloud(*floor_cloud, *floor_local, T_box_base.inverse());

        PointT min_pt, max_pt;
        pcl::getMinMax3D(*floor_local, min_pt, max_pt);

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

        PointT floor_min_pt_base, floor_max_pt_base;
        pcl::getMinMax3D(*floor_cloud, floor_min_pt_base, floor_max_pt_base);

        // Publish a floor-based grasp target. The manipulation node will apply
        // gripper offsets when it builds pre-grasp and grasp poses.
        geometry_msgs::PointStamped centroid_msg;
        centroid_msg.header.frame_id = target_frame;
        centroid_msg.header.stamp = source_stamp;
        centroid_msg.point.x = floor_centroid[0];
        centroid_msg.point.y = floor_centroid[1];
        centroid_msg.point.z = floor_min_pt_base.z + 0.02;
        //grasp_target_pub_.publish(centroid_msg);

        // Broadcast TF transform relative to base_footprint
        tf::Transform transform;
        transform.setOrigin(tf::Vector3(centroid_msg.point.x, centroid_msg.point.y, centroid_msg.point.z));
        transform.setRotation(tf::Quaternion(0, 0, 0, 1));
        //tf_broadcaster_.sendTransform(tf::StampedTransform(transform, source_stamp, target_frame, "clothes_grasp_target"));

        // Publish clothes point cloud in base_footprint
        sensor_msgs::PointCloud2 clothes_pc_msg;
        pcl::toROSMsg(*clothes_cloud, clothes_pc_msg);
        clothes_pc_msg.header.frame_id = target_frame;
        clothes_pc_msg.header.stamp = source_stamp;
        clothes_pc_pub_.publish(clothes_pc_msg);

        ROS_INFO_THROTTLE(2, "Detected floor-based grasp target: [%.3f, %.3f, %.3f] in base_footprint",
                          centroid_msg.point.x, centroid_msg.point.y, centroid_msg.point.z);
      }
      else if (cluster_class == "laundry basket")
      {
        sensor_msgs::PointCloud2 box_b_pc_msg;
        pcl::toROSMsg(*cluster_cloud, box_b_pc_msg);
        box_b_pc_msg.header.frame_id = target_frame;
        box_b_pc_msg.header.stamp = source_stamp;
        box_b_pc_pub_.publish(box_b_pc_msg);

        Eigen::Vector4f floor_centroid;
        pcl::compute3DCentroid(*floor_cloud, floor_centroid);

        // Publish target in base_footprint
        geometry_msgs::PointStamped centroid_msg;
        centroid_msg.header.frame_id = target_frame;
        centroid_msg.header.stamp = source_stamp;
        centroid_msg.point.x = floor_centroid[0];
        centroid_msg.point.y = floor_centroid[1];
        centroid_msg.point.z = floor_centroid[2];
        drop_target_pub_.publish(centroid_msg);

        // Broadcast TF transform relative to base_footprint
        tf::Transform transform;
        transform.setOrigin(tf::Vector3(floor_centroid[0], floor_centroid[1], floor_centroid[2]));
        transform.setRotation(tf::Quaternion(0, 0, 0, 1));
        tf_broadcaster_.sendTransform(tf::StampedTransform(transform, source_stamp, target_frame, "clothes_drop_target"));

        // Publish Floor PointCloud in base_footprint
        sensor_msgs::PointCloud2 floor_pc_msg;
        pcl::toROSMsg(*floor_cloud, floor_pc_msg);
        floor_pc_msg.header.frame_id = target_frame;
        floor_pc_msg.header.stamp = source_stamp;
        dest_floor_pc_pub_.publish(floor_pc_msg);
        box_b_floor_pc_pub_.publish(floor_pc_msg);

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