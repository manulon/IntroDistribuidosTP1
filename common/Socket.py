from socket import *

class Socket:
    def __init__(self, port, address):
        self.port = port
        self.address = address
        self.socket = socket(AF_INET, SOCK_DGRAM)

    def send(self, msg):
        self.socket.sendto(msg.encode(), (self.address, self.port))

    def receive(self):
        return self.socket.recvfrom(2048)
    
    def bind(self):
        self.socket.bind(('', self.port))

    def close(self):
        self.socket.close()