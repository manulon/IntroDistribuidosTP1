from common.Packet import Packet
from common.Utils import Utils
from common.constants import *

class ServerSelectiveRepeat:

    def __init__(self, socket, clientAddress, clientPort):
        self.socket = socket
        self.clientAddress = clientAddress
        self.clientPort = clientPort
        self.protocolID = bytes([0x1])
        self.window = []

    def send(self, message):
        self.socket.send(message, self.clientAddress, self.clientPort)

    def sendFileTransferTypeResponse(self):
        opcode = bytes([0x0])
        checksum = (2).to_bytes(4, BYTEORDER)
        nseq = (0).to_bytes(4, BYTEORDER)
        header = (opcode, checksum, nseq)

        # chunksize fijo (4096 bytes)
        chunksize = CHUNKSIZE.to_bytes(4, BYTEORDER)

        message = Packet.pack_file_transfer_type_response(header, chunksize)
        self.send(message)

        nextPacketIsADataPacket = False
        receivedPacketHeader, receivedPacketPayload = self.receivePackage()

        while not nextPacketIsADataPacket:
            if receivedPacketHeader['opcode'] == 1:
                self.send(message)
                receivedPacketHeader, receivedPacketPayload = self.receivePackage()
            else:
                nextPacketIsADataPacket = True

        return receivedPacketHeader, receivedPacketPayload
            
    def upload(self, filesize):
        # La funcion sendFileTransferTypeResponse() al asegurarse
        # de que llegó correctamente el paquete a destino, va a 
        # leer el primer paquete de la comunciacion y se lo va a 
        # pasar al protocolo para que siga haciendo las cosas.
        # Esto es debido a que es posible que esa respuesta se 
        # pierda, y en ese caso debe corroborarse que el proximo
        # paquete que llegue sea uno de los datos del archivo y 
        # no un retry del paquete que llego con anterioridad 
        # porque se perdio ese 'ACK' (el paquete 0001)
        header, payload = self.sendFileTransferTypeResponse()

        file = {}
        totalPackets = filesize / CHUNKSIZE
        distinctAcksSent = 0
        # Perdon por esta variable, no se me ocurria otra manera
        firstIteration = True

        for i in range(1,10):
            self.window.append({'nseq': i, 'isACKSent': False})

        while distinctAcksSent != totalPackets:
            if not firstIteration:
                header, payload = self.receivePackage()
            else:
                firstIteration = False

            if self.isChecksumOK(header, payload):
                self.sendACK(header['nseq'])
            
            for e in self.window:
                if (not e['isACKSent']) and header['nseq'] == e['nseq']:
                    e['isACKSent'] = True
                    distinctAcksSent += 1
            file[header['nseq'] - 1] = payload
                  
            if header['nseq'] == self.window[0]['nseq']:
                self.moveWindow()

        self.showFile(file)

    def download(self, filename):
        pass
    
    def receivePackage(self):
        received_message, (serverAddres, serverPort) = self.socket.receive(PACKET_SIZE)

        header, payload = Packet.unpack_package(received_message)

        return header, payload

    def sendACK(self, nseq):
        opcode = bytes([0x5])
        checksum = (2).to_bytes(4, BYTEORDER)
        nseqToBytes = nseq.to_bytes(4, BYTEORDER)
        header = (opcode, checksum, nseqToBytes)

        message = Packet.pack_ack(header)
        self.send(message)

    def moveWindow(self):
        while len(self.window) != 0 and self.window[0]['isACKSent']:
            lastNseq = self.window[-1]['nseq']
            self.window.pop(0)
            self.window.append({'nseq': lastNseq + 1, 'isACKSent': False})

    def showFile(self, file):
        content = b''
        fileArray = []
        for i in range(len(file)):
            fileArray.append(file[i])

        for e in fileArray:
            content += e            

        print('######################')
        print('El archivo se ha descargado! Su contenido es el siguiente:')
        print(content)

    def isChecksumOK(self, header, payload):
        # AGREGAR LÓGICA PARA RE-CALCULAR EL CHECKSUM
        checksumCalculado = 2
        return header['checksum'] == checksumCalculado