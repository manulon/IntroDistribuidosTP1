from socket import *
from common.Socket import Socket
from common.Packet import Packet
from common.constants import *
from server.ServerSelectiveRepeat import *
from server.ServerStopAndWait import *

class Server():
    MAX_FILE_SIZE = 4000000000 # 4GB

    def __init__(self, address, port):
        self.port = port
        self.address = address
        self.socket = Socket(self.port, self.address)
        self.protocol = None

    def receive(self):
        print('The server is ready to receive')
        while True:
            received_message, (clientAddress, clientPort) = self.socket.receive(FILE_TRANSFER_REQUEST_SIZE)
            opcode = int.from_bytes(received_message[:1], BYTEORDER)
            match opcode:
                case 0: # Upload
                    header, payload = Packet.unpack_upload_request(received_message)
                    if payload['protocol'] == 1:
                        print('Seleccionaste Selective Repeat')
                        protocol = ServerSelectiveRepeat(self.socket, clientAddress, clientPort)
                        self.protocol = protocol
                        self.protocol.sendFileTransferTypeResponse()
                        self.protocol.upload(payload['fileSize'])
                    else:
                        print('Seleccionaste Stop and Wait')
                        protocol = ServerStopAndWait(self.socket, clientAddress, clientPort)
                        self.protocol = protocol
                        self.protocol.sendFileTransferTypeResponse()
                        self.protocol.upload(payload['fileSize'])
                    break
                case 2: # Download
                    #print('downloading (stop and wait): '+ str(message))
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
