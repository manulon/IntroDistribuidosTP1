from socket import *
from common.Socket import Socket

class Client:
    def __init__(self, address, port):
        self.port = port
        self.serverPort = 16000
        self.address = address
        self.serverAddress = 'localhost'
        self.socket = Socket(self.port, self.address)

    def send(self, message):
        self.socket.send(message, self.serverAddress, self.serverPort)
        modifiedMessage, serverAddress = self.socket.receive()
        print(modifiedMessage.decode())

    def close(self):
        self.socket.close()