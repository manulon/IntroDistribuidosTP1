from socket import *
class Client:
    def __init__(self):
        self.server_port = 12000
        self.server_address = '127.0.0.1'

        self.socket = socket(AF_INET, SOCK_DGRAM)
    def send(self):
        message = input('Input lowercase sentence:')
        self.socket.sendto(message.encode(), (self.server_address, self.server_port))
        modifiedMessage, serverAddress = self.socket.recvfrom(2048)
        print(modifiedMessage.decode())
    def close(self):
        self.socket.close()