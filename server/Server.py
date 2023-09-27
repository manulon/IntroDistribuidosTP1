from socket import *
from common.Socket import Socket
from common.Packet import Packet
from server.ServerStopAndWait import StopAndWait
       
class Server():
    def __init__(self, address, port):
        self.port = port
        self.address = address
        self.socket = Socket(self.port, self.address)

    def receive(self):
        print('The server is ready to receive')
        while True:
            received_message, (clientAddress, clientPort) = self.socket.receive()
            _opcode = Packet.unpack_opcode(received_message[:1],received_message[:1])
            opcode = int.from_bytes(_opcode, byteorder='little') 
            #opcode, checksum, nseq, filename, filesize, md5 = Packet.unpack_upload_request(received_message)
            match opcode: 
                case 0: # Upload
                    _protocol = Packet.unpack_protocol(received_message[1:2],received_message[1:2])
                    protocol = int.from_bytes(_protocol, byteorder='little')
                    if protocol == 1:
                       print('Seleccionaste Selective Repeat')
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

    def close(self):
        self.socket.close()
