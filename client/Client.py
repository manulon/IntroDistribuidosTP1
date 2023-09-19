from socket import *
from common.Socket import Socket

class Client:
    def __init__(self):
        self.port = 12001
        self.serverPort = 12000
        self.address = '127.0.0.1'
        self.serverAddress = '127.0.0.1'
        self.socket = Socket(self.port, self.address)

    def send(self):
        message = input('Input lowercase sentence:')
        self.socket.send(message.encode(), self.serverAddress, self.serverPort)
        modifiedMessage, serverAddress = self.socket.receive()
        print(modifiedMessage.decode())

    def close(self):
        self.socket.close()