from socket import *
from common.Socket import Socket

class Client:
    def __init__(self, address, port):
        self.port = port
        self.serverPort = 16000
        self.address = address
        self.serverAddress = 'localhost'
        self.socket = Socket(self.port, self.address)
        self.protocol = None

    def upload(self, filename):
        self.protocol.upload(filename)

    def setProtocol(self, protocol):
        protocol.setServerInfo(self.serverAddress, self.serverPort, self.socket)
        self.protocol = protocol
        
    def close(self):
        self.socket.close()