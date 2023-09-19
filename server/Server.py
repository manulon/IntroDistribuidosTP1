from socket import *

class Server():
    def __init__(self):
        self.server_port = 12000
        self.server_address = '127.0.0.1'
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.bind(('', self.server_port))
    def receive(self):
        print('The server is ready to receive')
        while True:
            message, clientAddress = self.socket.recvfrom(2048)
            modifiedMessage = message.decode().upper()
            self.socket.sendto(modifiedMessage.encode(), clientAddress)
    def close(self):
        self.socket.close()
