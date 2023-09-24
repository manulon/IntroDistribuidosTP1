from socket import *
from common.Socket import Socket
       
class Server():
    def __init__(self, address, port):
        self.port = port
        self.address = address
        self.socket = Socket(self.port, self.address)

    def receive(self):
        print('The server is ready to receive')
        while True:
            message, (clientAddress, clientPort) = self.socket.receive()
            modifiedMessage = message.decode().upper()
            self.socket.send(modifiedMessage.encode(), clientAddress, clientPort)

    def close(self):
        self.socket.close()
