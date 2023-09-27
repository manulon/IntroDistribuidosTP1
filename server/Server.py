from socket import *
from common.Socket import Socket
from common.Packet import Packet
from server.StopAndWait import StopAndWait
       
class Server():
    def __init__(self, address, port):
        self.port = port
        self.address = address
        self.socket = Socket(self.port, self.address)

    def receive(self):
        print('The server is ready to receive')
        while True:
            received_message, (clientAddress, clientPort) = self.socket.receive()            
            opcode, message =Packet.unpack_upload_request(received_message,received_message)            
            #opcode, checksum, nseq, filename, filesize, md5 = Packet.unpack_upload_request(received_message)
            match opcode: 
                case 0: # Upload
                    StopAndWait.upload()
                    break
                case 2: # Download
                    print('downloading (stop and wait): '+ str(message))
                    #StopAndWait.download()
                    break
                case 7: # List
                    #StopAndWait.list(message)
                    break
                case default:
                    # print("message not understood")
                    # close connection
                    break
            #modifiedMessage = message.decode().upper()

    def close(self):
        self.socket.close()
