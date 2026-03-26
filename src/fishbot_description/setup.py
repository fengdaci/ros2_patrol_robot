import os
from setuptools import setup

package_name = 'fishbot_description'

# 定义一个函数：安全获取目录下的文件（目录不存在时返回空列表）
def get_files(dir_path):
    file_list = []
    if os.path.exists(dir_path):
        for f in os.listdir(dir_path):
            if f.endswith(('.urdf', '.xacro')):
                file_list.append(os.path.join(dir_path, f))
    return file_list

# 要安装的文件列表
data_files = [
    ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
    ('share/' + package_name, ['package.xml']),
    # 安装urdf根目录
    (os.path.join('share', package_name, 'urdf'), 
     get_files('urdf')),
    # 安装urdf/fishbot子目录
    (os.path.join('share', package_name, 'urdf/fishbot'), 
     get_files('urdf/fishbot')),
    # 安装urdf/fishbot/sensor子目录（如果目录不存在，自动跳过，不报错）
    (os.path.join('share', package_name, 'urdf/fishbot/sensor'), 
     get_files('urdf/fishbot/sensor')),
]

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=data_files,
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='daci',
    maintainer_email='daci@todo.todo',
    description='Fishbot description package',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={'console_scripts': []},
)
