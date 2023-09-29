from socket import *
from common.Socket import Socket
from common.Packet import Packet
from common.constants import *
from server.ServerSelectiveRepeat import *

class Server():
    def __init__(self, address, port):
        self.port = port
        self.address = address
        self.socket = Socket(self.port, self.address)
        self.protocol = None

    def receive(self):
        print('The server is ready to receive')
        while True:
            firstPacketIsValid = False
            while not firstPacketIsValid:
                firstPacketIsValid, header, payload, clientAddress, clientPort = self.receiveFirstPacket()
            
            match header['opcode']:
                case 0: # Upload
                    if payload['protocol'] == 1:
                        print('Seleccionaste Selective Repeat')
                        protocol = ServerSelectiveRepeat(self.socket, clientAddress, clientPort)
                        self.protocol = protocol
                        self.protocol.upload(payload['fileSize'])
                    else:
                        print('Seleccionaste Stop and Wait')
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

    def receiveFirstPacket(self):
        received_message, (clientAddress, clientPort) = self.socket.receive(FILE_TRANSFER_REQUEST_SIZE)
        header, payload = Packet.unpack_upload_request(received_message)

        firstPacketIsValid = self.isChecksumOK(header, payload)

        return firstPacketIsValid, header, payload, clientAddress, clientPort

    def isChecksumOK(self, header, payload):
        # AGREGAR LÓGICA PARA RE-CALCULAR EL CHECKSUM
        checksumCalculado = 2
        return header['checksum'] == checksumCalculado

    def close(self):
        self.socket.close()
