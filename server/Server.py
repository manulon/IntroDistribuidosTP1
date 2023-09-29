import queue
from socket import *
from common.Socket import Socket
from common.Packet import Packet
from common.constants import *
from server.ServerSelectiveRepeat import *
from server.UDPReceivingThread import *
from server.UDPSendingThread import *

class Server():
    def __init__(self, address, port):
        self.port = port
        self.address = address
        self.socket = Socket(self.port, self.address)
        self.protocol = None
        self.clients = {}

    def start(self):
        #if self.verbosity >= 1:
        print(f"{COLOR_BLUE}[INFO]{COLOR_END}"f" - Starting the Server...")
        #self.createThreads()

        print("\033[1mTo close the server type 'q':\033[0m")
        while True:
            user_input = input()
            if user_input == 'q':
                print(f"{COLOR_BLUE}[INFO]{COLOR_END}"
                     " - Closing the Server...")
                #self.udp_sending_thread.force_stop()
                #self.udp_receiving_thread.force_stop()

                #self.udp_receiving_thread.join()
                #self.udp_sending_thread.join()
                print(f"{COLOR_BLUE}[INFO]{COLOR_END}"
                    " - The Server has been succesfully closed.")
                break
            else:
                print("\033[1mThe key entered is invalid. To close the server type 'q':\033[0m")

        '''
        #################################
        Esto tiene que ir en otro archivo
        #################################

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
        '''

    def createThreads(self):
        self.udp_sending_queue = queue.Queue()
        self.udp_receiving_thread = UDPReceivingThread()
        self.udp_sending_thread = UDPSendingThread()

        self.udp_receiving_thread.start()
        self.udp_sending_thread.start()

        print(f"{COLOR_BLUE}[INFO]{COLOR_END}"
            " - UDP Server started.")

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
