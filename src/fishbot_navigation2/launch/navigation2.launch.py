# 导入系统模块
import os
# 导入launch基础模块
import launch
# 导入launch_ros模块用于启动ROS2节点
import launch_ros
# 从ament索引中获取功能包共享目录的函数
from ament_index_python.packages import get_package_share_directory
# 导入PythonLaunchDescriptionSource用于加载其他launch文件
from launch.launch_description_sources import PythonLaunchDescriptionSource

# 定义launch文件的核心函数，返回LaunchDescription对象
def generate_launch_description():
    # 获取fishbot_navigation2功能包的共享目录路径
    fishbot_navigation2_dir = get_package_share_directory(
        'fishbot_navigation2'
    )
    # 获取nav2_bringup功能包的共享目录路径
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')
    # 拼接nav2默认rviz配置文件的路径
    rviz_config_dir = os.path.join(
        nav2_bringup_dir, 'rviz', 'nav2_default_view.rviz'
    )

    # 声明launch参数：是否使用仿真时间（默认true）
    use_sim_time = launch.substitutions.LaunchConfiguration(
        'use_sim_time', default='true'
    )
    # 声明launch参数：地图文件路径（默认拼接为fishbot_navigation2/maps/room.yaml）
    map_yaml_path = launch.substitutions.LaunchConfiguration(
        'map', default=os.path.join(fishbot_navigation2_dir, 'maps', 'room.yaml')
    )
    # 声明launch参数：Nav2参数文件路径（默认拼接为fishbot_navigation2/config/nav2_params.yaml）
    nav2_param_path = launch.substitutions.LaunchConfiguration(
        'params_file', default=os.path.join(fishbot_navigation2_dir, 'config', 'nav2_params.yaml')
    )

    # 构建并返回LaunchDescription对象，包含启动逻辑
    return launch.LaunchDescription([
        # 声明use_sim_time参数的描述与默认值
        launch.actions.DeclareLaunchArgument('use_sim_time', default_value=use_sim_time,
                                            description='Use simulation (Gazebo) clock if true'),
        # 声明map参数的描述与默认值
        launch.actions.DeclareLaunchArgument('map', default_value=map_yaml_path,
                                            description='Full path to map file to load'),
        # 声明params_file参数的描述与默认值
        launch.actions.DeclareLaunchArgument('params_file', default_value=nav2_param_path,
                                            description='Full path to param file to load'),

        # 包含nav2_bringup的bringup_launch.py启动文件
        launch.actions.IncludeLaunchDescription(
            PythonLaunchDescriptionSource([nav2_bringup_dir, '/launch', '/bringup_launch.py']),
            # 向被包含的launch文件传递参数
            launch_arguments={
                'map': map_yaml_path,
                'use_sim_time': use_sim_time,
                'params_file': nav2_param_path
            }.items(),
        ),

        # 启动rviz2节点
        launch_ros.actions.Node(
            package='rviz2',        # 节点所属功能包
            executable='rviz2',     # 要执行的可执行文件
            name='rviz2',           # 节点名称
            arguments=['-d', rviz_config_dir],  # 传入rviz配置文件路径参数
            parameters=[{'use_sim_time': use_sim_time}],  # 传递仿真时间参数
            output='screen'        # 节点输出打印到终端
        ),
    ])