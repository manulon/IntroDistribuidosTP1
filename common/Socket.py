from socket import *

class Socket:
    def __init__(self, port, address):
        self.port = port
        self.address = address
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.bind(('', self.port))

    def send(self, msg, address, port):
        self.socket.sendto(msg, (address, port))

    # bufsize: bytes que debo recibir
    def receive(self, bufsize):
        return self.socket.recvfrom(bufsize)      

    def close(self):
        self.socket.close()

    def settimeout(self, time):
        self.socket.settimeout(time)