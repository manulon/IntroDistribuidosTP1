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
        while self.allowedToRun:
            firstPacketIsValid = False
            if not firstPacketIsValid:
                try:
                    self.serverSocket.settimeout(0.2)
                    firstPacketIsValid, header, payload, clientAddress, clientPort = self.receiveFirstPacket()
                    if firstPacketIsValid:
                        if (clientAddress, clientPort) not in self.clients:
                            print(
                                f"{COLOR_BLUE}[INFO]"
                                f"{COLOR_END}"
                                f" - New UDP Client {clientAddress}"
                                f":{clientPort} connected.")
                        match payload['protocol']:
                            case 0: # STOP & WAIT
                                print('Seleccionaste stop and wait')
                                break
                            case 1: # SELECTIVE REPEAT    
                                print('Seleccionaste Selective Repeat')

                                self.lastSocketPort += 1
                                newSocket = Socket(self.lastSocketPort, self.serverAddress)
                                self.clients[(clientAddress, clientPort)] = UDPServerThread(
                                    ServerSelectiveRepeat(newSocket, clientAddress, clientPort),
                                    header, payload
                                )
                                self.clients[(clientAddress, clientPort)].start()
                                print('Mi cliente terminó')
                                break
                except:
                    print('Tiro except, no me importa nada igual')
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