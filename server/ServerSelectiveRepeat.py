from common.Packet import Packet
from common.Utils import Utils
from common.constants import *

class ServerSelectiveRepeat:

    def __init__(self, socket, clientAddress, clientPort):
        self.socket = socket
        self.clientAddress = clientAddress
        self.clientPort = clientPort
        self.protocolID = bytes([SELECTIVE_REPEAT])
        self.window = []

    def send(self, message):
        self.socket.send(message, self.clientAddress, self.clientPort)

    def sendFileTransferTypeResponse(self):
        opcode = bytes([0x0])
        checksum = (2).to_bytes(4, BYTEORDER)
        nseq = (0).to_bytes(4, BYTEORDER)
        header = (opcode, checksum, nseq)

        # fixed chunksize (4096 bytes)
        chunksize = CHUNKSIZE.to_bytes(4, BYTEORDER)

        message = Packet.pack_file_transfer_type_response(header, chunksize)
        self.send(message)

    def upload(self, filesize):
        file = {}
        totalPackets = filesize / CHUNKSIZE
        acksSent = 0
        for i in range(10):
            self.window.append({'nseq': i, 'isACKSent': False})

        while acksSent != totalPackets:
            header, payload = self.receivePackage()
            self.sendACK(header['nseq'])
            for e in self.window:
                if header['nseq'] == e['nseq']:
                    e['isACKSent'] == True
            acksSent += 1
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
        opcode = bytes([ACK_OPCODE])
        checksum = (2).to_bytes(4, BYTEORDER)
        nseqToBytes = nseq.to_bytes(4, BYTEORDER)
        header = (opcode, checksum, nseqToBytes)

        message = Packet.pack_ack(header)
        self.send(message)

    def moveWindow(self):
        while self.window.length() != 0 and self.window[0].isACKSent == True:
            lastNseq = self.window[-1].nseq
            self.window.pop()
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