from ament_index_python.packages import get_package_share_directory
import os
import launch
import launch_ros


def generate_launch_description():
    # 功能包路径
    urdf_package_path = get_package_share_directory('fishbot_description')
    # urdf路径
    default_urdf_path = os.path.join(urdf_package_path, 'urdf', 'first_robot.urdf')
    # rviz路径
    default_rviz_config_path = os.path.join(urdf_package_path, 'config', 'display_robot_model.rviz')

    # 声明参数
    action_declare_arg_model_path = launch.actions.DeclareLaunchArgument(
        name='model', # 参数名，在后面使用的时候要保持一致 substitution['model'] 获取更多参数的值
        # 启动节点的时候也可以 运行 launch launch firstbot_description/launch/display_robot_model.launch.py model:=/xxx/xxx.urdf 来覆盖默认值，无需修改Launch文件代码。
        # 如果启动时未指定参数，那么默认值为：robot.urdf; 但是当urdf路径错误，Launch文件也会报错。
        default_value=str(default_urdf_path),
        description='Robot的模型文件的路径. 执行 ros2 launch 包含该文件的launch文件时,使用 --show-args 时会显示该描述。方便使用者理解参数用途。'
    )

    # 获取该参数值，供节点用，并使得该参数值，以供给 robot_state_publisher 相关子进程在 跨进程
    # 相当于在命令行 - 模式中内容可写为： launch_ros.actions.Node( command 这个参数的值的字符串形式，但这里LaunchConfiguration(model)
    # 才是正确写法。 command 内的参数是一个字符串，类似于 ros2 run 那样的，参数的顺序，位置等。)
    action_robot_state_publisher_node = launch_ros.actions.Node(
        # 让上一步获取的 urdf 文件内容，能够被 ros 节点读取和解析到
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': launch.substitutions.Command(['xacro ', launch.substitutions.LaunchConfiguration('model')])}],
        # value_type = str) 等声明两个参数的类型是否是字符串。同 robot_state_publisher 节点的 robot_description 参数要求保持字符串类型的 XML 文件。避免 ros 2 启动解析的时候出现“类型不匹配”错误。
    )

    # 关节发布节点
    joint_state_publisher_node = launch_ros.actions.Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
    )

    # rviz2 显示
    action_rviz_node = launch_ros.actions.Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', default_rviz_config_path])
       

    # 启动所有节点
    return launch.LaunchDescription([
        action_declare_arg_model_path,
        action_robot_state_publisher_node,
        joint_state_publisher_node,
        action_rviz_node
    ])