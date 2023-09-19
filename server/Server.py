from socket import *
from common.Socket import Socket
       
class Server():
    def __init__(self):
        self.port = 12000
        self.address = '127.0.0.1'
        self.socket = Socket(self.port, self.address)

    def receive(self):
        print('The server is ready to receive')
        while True:
            message, (clientAddress, clientPort) = self.socket.receive()
            modifiedMessage = message.decode().upper()
            self.socket.send(modifiedMessage.encode(), clientAddress, clientPort)

    def close(self):
        self.socket.close()
