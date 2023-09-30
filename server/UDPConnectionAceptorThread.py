import threading
from common.constants import *
from common.Socket import *
from server.UDPServerThread import *
from server.ServerSelectiveRepeat import *

class UDPConnectionAceptorThread(threading.Thread):

    def __init__(self, serverSocket, clients):
        threading.Thread.__init__(self)
        self.serverSocket = serverSocket
        self.clients = clients
        self.allowedToRun = True
        self.lastSocketPort = serverSocket.getPort()
        self.serverAddress = serverSocket.getAddress()

    def run(self):
        print('0')
        while self.allowedToRun:
            print('1')
            firstPacketIsValid = False
            print('2')
            while not firstPacketIsValid:
                print('3')
                firstPacketIsValid, header, payload, clientAddress, clientPort = self.receiveFirstPacket()
                print('4')
                if (clientAddress, clientPort) not in self.clients:
                    print('5')
                    print(
                        f"{COLOR_BLUE}[INFO]"
                        f"{COLOR_END}"
                        f" - New UDP Client {clientAddress}"
                        f":{clientPort} connected.")
                    print('6')
                match payload['protocol']:
                    case 0: # STOP & WAIT
                        print('7')
                        print('Seleccionaste stop and wait')
                        print('8')
                        break
                    case 1: # SELECTIVE REPEAT    
                        print('9')
                        print('Seleccionaste Selective Repeat')
                        
                        self.lastSocketPort += 1
                        print('10')
                        newSocket = Socket(self.lastSocketPort, self.serverAddress)
                        print('11')
                        self.clients[(clientAddress, clientPort)] = UDPServerThread(
                            ServerSelectiveRepeat(newSocket, clientAddress, clientPort),
                            header, payload
                        )
                        print('12')
                        self.clients[(clientAddress, clientPort)].start()
                        print('13')
                        print('Mi cliente terminó')
                        break
                print('14')
                #modifiedMessage = message.decode().upper()
        print('Sali del while de conexion aceptador')

    def receiveFirstPacket(self):
        received_message, (clientAddress, clientPort) = self.serverSocket.receive(FILE_TRANSFER_REQUEST_SIZE)
        header, payload = Packet.unpack_upload_request(received_message)

        firstPacketIsValid = self.isChecksumOK(header, payload)

        return firstPacketIsValid, header, payload, clientAddress, clientPort

    def isChecksumOK(self, header, payload):
        # AGREGAR LÓGICA PARA RE-CALCULAR EL CHECKSUM
        checksumCalculado = 2
        return header['checksum'] == checksumCalculado

    def force_stop(self):
        print('¿Entre aca?')
        self.allowedToRun = False
        self.serverSocket.close()
        for k in self.clients.keys():
            self.clients[k].force_stop()
        print('Estoy seguro que esto se printea')
        for k in self.clients.keys():
            print('Voy a cerrar el fclente')
            self.clients[k].join()
            print('¡¡¡¡LOCERRE!!!!')

        print('Supuestamente cerre todo')