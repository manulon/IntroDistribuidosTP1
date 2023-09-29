from common.Packet import Packet
from common.Hasher import Hasher
from common.constants import *

class ServerStopAndWait:
    def __init__(self, socket, clientAddress, clientPort):
        self.socket = socket
        self.clientAddress = clientAddress
        self.clientPort = clientPort
        self.protocolID = bytes([STOP_AND_WAIT])

    def send(self, message):
        self.socket.send(message, self.clientAddress, self.clientPort)

    def sendFileTransferTypeResponse(self):
        opcode = bytes([0x1])
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
        nextNseq = 1
        file = []

        while acksSent < totalPackets:
            header, payload = self.receivePackage()
            print(header)
            if header['nseq'] == nextNseq:
                package = Packet.pack_package(header, payload)
                if header['checksum'] == Hasher.checksum(package):
                    self.sendACK(header['nseq'])
                    file.append(payload)
                    nextNseq = acksSent % 2
                    acksSent += 1
                else:
                    print('Error de checksum')
                    #self.sendInvalidChecksum()
            else: # client resends packet - cases 3 (lost ACK) and 4 (timeout)
                self.sendACK(header['nseq']) # server only resends ACK (detects duplicate)

        self.showFileAsBytes(file)

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

    def showFileAsBytes(self, fileArray):
        content = b''
        for e in fileArray:
            content += e  
        print('######################')
        print('El archivo se ha descargado! Su contenido es el siguiente:')
        print(content)