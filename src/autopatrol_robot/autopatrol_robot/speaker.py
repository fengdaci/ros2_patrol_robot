import rclpy
from rclpy.node import Node
from autopatrol_interfaces.srv import SpeechText
import espeakng

class Speaker(Node):
    def __init__(self,node_name):
        super().__init__(node_name)
        #创建一个服务端
        self.speech_service = self.create_service(SpeechText,'speech_text',self.speak_text_callback)#传进一个（消息接口，服务名字，服务的回调函数）
        self.speaker_= espeakng.Speaker()
        self.speaker_.voice='zh'
    #定义回调函数
    def speak_text_callback(self,request,response):
        self.get_logger().info(f'正在准备朗读{request.text}')
        self.speaker_.say(request.text)
        self.speaker_.wait() 
        response.result= True
        return response 

def main(args=None):
    rclpy.init(args=args)
    node = Speaker ('speaker' )
    rclpy.spin(node)
    rclpy.shutdown()