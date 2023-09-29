import math
import time
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
            if receivedPacketHeader['opcode'] == 0:
                self.send(message)
                receivedPacketHeader, receivedPacketPayload = self.receivePackage()
            else:
                nextPacketIsADataPacket = True

        return receivedPacketHeader, receivedPacketPayload
            
    def upload(self, filesize):
        header, payload = self.sendFileTransferTypeResponse()

        file = {}
        totalPackets = math.ceil(filesize / CHUNKSIZE)
        distinctAcksSent = 0
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

        self.stopFileTransfer(totalPackets+1)

        self.showFile(file)

    def download(self, filename):
        pass
    
    def receivePackage(self):
        received_message, (serverAddres, serverPort) = self.socket.receive(PACKET_SIZE)

        if Utils.bytesToInt(received_message[:1]) == 0:
            header, payload = Packet.unpack_upload_request(received_message)
        else:
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
        print('######################')
        print('######################')
        print(content)

    def isChecksumOK(self, header, payload):
        # AGREGAR LÓGICA PARA RE-CALCULAR EL CHECKSUM
        checksumCalculado = 2
        return header['checksum'] == checksumCalculado
    
    def stopFileTransfer(self, nseq):
        opcode = bytes([0x6])
        checksum = (2).to_bytes(4, BYTEORDER)
        nseqToBytes = nseq.to_bytes(4, BYTEORDER)
        header = (opcode, checksum, nseqToBytes)

        md5 = (2).to_bytes(4, BYTEORDER)    # 16 bytes, deben calcularse
        state = bytes([0x1])                # harcodeado (1 ok, 0 no ok)
        payload = (md5, state)

        message = Packet.pack_stop_file_transfer(header, payload)
    
        self.send(message)
        stopFileTransferMsgSentAt = time.time()

        communicationFinished = False
        stopCommunicationSocketTimeout = 0

        while (not communicationFinished) and (stopCommunicationSocketTimeout < LAST_ACK_PACKET_TIMEOUT):
           try:
               self.socket.settimeout(0.2)
               received_message, (serverAddres, serverPort) = self.socket.receive(ACK_SIZE)
               stopCommunicationSocketTimeout = 0
               communicationFinished = True
           except TimeoutError:
               # Acá se da por sentado que el cliente se cerró
               stopCommunicationSocketTimeout += 1

           if (not communicationFinished) and (time.time() - stopFileTransferMsgSentAt > SELECTIVE_REPEAT_PACKET_TIMEOUT):
                self.send(message)
                stopFileTransferMsgSentAt = time.time()            
