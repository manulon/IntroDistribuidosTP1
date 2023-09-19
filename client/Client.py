from socket import *
from common.Socket import Socket

class Client:
    def __init__(self):
        self.socket = Socket(12000, '181.2.159.225')

    def send(self):
        message = input('Input lowercase sentence:')
        self.socket.send(message)
        modifiedMessage, serverAddress = self.socket.receive()
        print(modifiedMessage.decode())

    def close(self):
        self.socket.close()