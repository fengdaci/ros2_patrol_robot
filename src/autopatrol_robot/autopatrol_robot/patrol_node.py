import rclpy
# 导入ROS2标准位姿消息：Pose是基础位姿（位置+姿态），PoseStamped是带时间戳/坐标系的位姿（导航专用）
from geometry_msgs.msg import PoseStamped, Pose
# 导入Nav2简易导航器：BasicNavigator封装了所有导航核心操作，TaskResult用于判断导航结果
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
# 导入TF坐标变换工具：监听/查询不同坐标系之间的位姿变换
from tf2_ros import TransformListener, Buffer
# 导入欧拉角↔四元数转换工具：ROS2用四元数表示姿态，人类更易理解欧拉角（yaw偏航角）
from tf_transformations import euler_from_quaternion, quaternion_from_euler
# 导入ROS2时长类：用于设置导航超时、等待时长等
from rclpy.duration import Duration 
import sys
from autopatrol_interfaces.srv import SpeechText 
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2


# 定义巡逻导航节点类，继承BasicNavigator（复用Nav2导航核心功能）
class PartolNode(BasicNavigator):
    # 构造函数：初始化节点，声明/获取导航参数
    def __init__(self, node_name='patrol_node'):
        # 调用父类BasicNavigator的构造函数，完成导航器节点的基础初始化
        super().__init__(node_name)
        
        # 声明ROS2参数：initial_point（机器人初始位姿），格式[x, y, yaw]（单位：米/弧度）
        # 默认值[0.0, 0.0, 0.0]：表示地图原点，偏航角0（朝向正前方）
        self.declare_parameter('initial_point', [0.0, 0.0, 0.0])
        
        # 声明ROS2参数：target_points（巡逻目标点列表），格式[x1,y1,yaw1, x2,y2,yaw2, ...]
        # 默认值[0.0,0.0,0.0, 1.0,1.0,1.57]：表示2个目标点，第二个点yaw=1.57≈90度（朝右）
        self.declare_parameter('target_points', [0.0, 0.0, 0.0, 1.0, 1.0, 1.57])
        
        #value取出这个选项的实际数值（优先取外部配置的值，没有就取默认值）,	获取参数的原始值（ROS2 参数对象的 value 属性，返回参数的实际数据）
        
        # 获取声明的初始位姿参数值，赋值给实例变量（后续设置初始位姿用）
        self.initial_point_ = self.get_parameter('initial_point').value
        # 获取声明的巡逻目标点参数值，赋值给实例变量（后续遍历导航用）
        self.target_points_ = self.get_parameter('target_points').value
        self.buffer_ = Buffer()
        self.tf_listener_ = TransformListener(self.buffer_, self)
        
        
         #语音合成客户端
        self.speach_client = self.create_client(SpeechText,'speech_text')

        self.declare_parameter('image_save_path', '')
        self.image_save_path = self.get_parameter('image_save_path').value
        self.bridge = CvBridge()
        self.latest_image = None
        self.subscription_image = self.create_subscription(
            Image,
            '/camera_sensor/image_raw',
            self.image_callback,
            10
        )
    
    
    def get_pose_by_xyyaw(self, x, y, yaw):
        """
        通过x,y,yaw合成PoseStamped
        """
        # 1. 创建空的PoseStamped消息对象（Nav2导航的核心位姿格式）
        pose= PoseStamped()
    
        # 2. 设置消息头：指定坐标系（必须是map，Nav2以map为导航基准）
        pose.header.frame_id = "map"
        # 3. 设置消息头：添加当前时间戳（保证消息时效性，Nav2会忽略无时间戳的消息）
        pose.header.stamp = self.get_clock().now().to_msg()
    
        # 4. 设置位置信息：平面导航z轴固定为0（RM仿真机器人在地面移动）
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.position.z = 0.0
    
        # 5. 设置姿态信息：将欧拉角(yaw)转换为四元数（ROS2规定用四元数表示姿态，避免万向锁）
        # quaternion_from_euler(roll, pitch, yaw)：roll/pitch固定为0（平面导航无翻滚/俯仰）
        rotation_quat= quaternion_from_euler(0.0, 0.0, yaw)
        pose.pose.orientation.x = rotation_quat[0]
        pose.pose.orientation.y = rotation_quat[1]
        pose.pose.orientation.z = rotation_quat[2]
        pose.pose.orientation.w = rotation_quat[3]
    
        # 6. 返回合成好的导航位姿消息
        return pose

    def init_robot_pose(self):
        """
        初始化机器人位姿（替代RViz手动点2D Pose Estimate）
        从initial_point参数读取x/y/yaw，自动设置为机器人初始位姿
        """
        #从参数获取初始化点
        self.initial_point_ = self.get_parameter('initial_point').value
        #合成位姿并进行初始化
        self.setInitialPose(self.get_pose_by_xyyaw(self.initial_point_[0], self.initial_point_[1], self.initial_point_[2]))
        #等待导航激活
        self.waitUntilNav2Active() 

    def get_target_points(self):
        """
        通过参数值获取目标点集合
        """
        points = []
        self.target_points_ = self.get_parameter('target_points').value
        
        #[x1, y1, yaw1, x2, y2, yaw2, ...]（比如 2 个目标点就是 [0,0,0,1,1,1.57]
        #循环两次，3个元素为一组
        for index in range(int(len(self.target_points_)/3)):
            x = self.target_points_[index*3]
            y = self.target_points_[index*3+1]
            yaw = self.target_points_[index*3+2]
            #把每个目标点的 x/y/yaw 打包成独立的列表，添加到 points 中
            points.append([x,y,yaw])
            #当 index=0：输出 获取到目标点：0->(0.0,0.0,0.0)；
            #当 index=1：输出 获取到目标点：1->(1.0,1.0,1.57)。
            self.get_logger().info(f'获取到目标点：{index}->({x},{y},{yaw})')
        #就是把函数内部解析好的目标点列表，“传递出去” 给调用这个函数的代码，让外部可以调用
        return points     
        

    def nav_to_pose(self, target_pose):
        """
        导航到指定位姿
        """    
        self.goToPose(target_pose)

        while not self.isTaskComplete():
            feedback = self.getFeedback()
            self.get_logger().info(f'剩余距离：{feedback.distance_remaining}')
        result = self.getResult()
        if result == TaskResult.SUCCEEDED:
            self.get_logger().info('导航结果：成功')
        elif result == TaskResult.CANCELED:
            self.get_logger().warn('导航结果：被取消')
        elif result == TaskResult.FAILED:
            self.get_logger().error('导航结果：失败')
        else:
            self.get_logger().error('导航结果：状态无效')
        return result



    def get_current_pose(self):
        """
        通过TF获取当前位姿
        """
        while rclpy.ok():
            try:
                result = self.buffer_.lookup_transform('map','base_footprint',
                            rclpy.time.Time(seconds=0.0),Duration(seconds = 1.0))
                transform = result.transform
                self.get_logger().info(f'平移：{transform.translation}')
                # self.get_logger().info(f'旋转：{transform.rotation}')
                # rotation_euler = euler_from_quaternion([
                #     transform.rotation.x,
                #     transform.rotation.y,
                #     transform.rotation.z,
                #     transform.rotation.w,
                #     ])
                # self.get_logger().info(f'平移：{transform.translation},旋转四元数：{transform.rotation}')
                return transform
            
            except Exception as e:
                self.get_logger().warn(f'获取坐标变换失败：原因{str(e)}')


    def speach_text(self, text):#text：函数的入参，是要转换成语音的文本内容（比如传入"正在初始化位置"）。
        ## 调用服务播放语音##
        #self.speach_client：是节点中提前创建的「服务客户端对象」，专门用来和语音合成服务端通信
        #客户端尝试连接服务端，timeout_sec=1.0表示每次尝试最多等 1 秒；返回值是布尔值（服务上线返回True，没上线返回False）
        while not self.speach_client.wait_for_service(timeout_sec=1.0): 
            self.get_logger().info('语音合成服务未上线，等待中...')  
        
        #SpeechText：是你自定义的服务类型（对应autopatrol_interfaces/srv/SpeechText.srv文件）。
        #.Request()：服务的 “请求部分”（对应 srv 文件中---上面的内容，比如string text），这行相当于创建一个 “空白的请求表单”
        request = SpeechText.Request()
        
        #给请求对象赋值：把传入的text参数（比如 “位置初始化完成”）填到请求表单的text字段里，这样服务端就能收到要合成的文本内容。
        request.text = text
        #call_async(request)：客户端把填好的请求发送给服务端，这是「异步调用」（不会卡住节点的其他功能，比如导航）。
        future = self.speach_client.call_async(request)  
        
        #rclpy.spin_until_future_complete：ROS 2 的工具函数，让当前节点暂时 “保持运行（自旋）”，直到future对应的服务请求处理完成（服务端返回结果），才继续执行后面的代码。
        #self：传入当前节点对象，确保自旋时节点能正常接收服务端的响应。
        rclpy.spin_until_future_complete(self, future) 
        
        if future.done():
            result = future.result()
            if result.result:  
                self.get_logger().info(f'语音合成成功:{text}') 
            else:
                self.get_logger().warn(f'语音合成失败:{text}') 
        else:
            self.get_logger().warn('语音合成服务请求失败')  

    def image_callback(self, msg):
        # 将最新的消息放到 latest_image中
        self.latest_image = msg
    
    def record_image(self):
        # 记录图像
        if self.latest_image is not None:
            pose = self.get_current_pose()
            cv_image = self.bridge.imgmsg_to_cv2(self.latest_image)
            cv2.imwrite(f"{self.image_save_path}image_{pose.translation.x:.2f}_{pose.translation.y:.2f}.png", cv_image)




def main():
    rclpy.init()
    patrol = PartolNode()
    #只是为了生成参数
    #rclpy.spin(patrol)
    #初始化机器人位置
    patrol.speach_text(text='正在初始化位置')
    patrol.init_robot_pose()
    patrol.speach_text(text='位置初始化完成')

    while rclpy.ok():
        points = patrol.get_target_points()
        for point in points:
            x,y,yaw = point[0],point[1],point[2]
            #导航到目标点
            target_pose = patrol.get_pose_by_xyyaw(x,y,yaw)
            patrol.speach_text(text=f'准备前往目标点{x},{y}')
            patrol.nav_to_pose(target_pose) 
            patrol.speach_text(text=f"已到达目标点{x},{y}，准备记录图像")
            patrol.record_image()
            patrol.speach_text(text=f"图像记录完成")   
    
    
    rclpy.shutdown()




        