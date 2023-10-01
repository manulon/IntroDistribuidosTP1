import hashlib
import os
import math
import time
from common.Packet import Packet
from common.Utils import Utils
from common.constants import *
from common.Logger import *
from common.Checksum import *

class ServerSelectiveRepeat:

    def __init__(self, socket, clientAddress, clientPort, storage):
        self.socket = socket
        self.clientAddress = clientAddress
        self.clientPort = clientPort
        self.protocolID = bytes([SELECTIVE_REPEAT])
        self.window = []
        self.storage = storage

    def send(self, message):
        self.socket.send(message, self.clientAddress, self.clientPort)

    def sendFileTransferTypeResponse(self):
        opcode = bytes([FILE_TRANSFER_RESPONSE_OPCODE])
        zeroedChecksum = (0).to_bytes(4, BYTEORDER)
        nseq = (0).to_bytes(4, BYTEORDER)
        finalChecksum = Checksum.get_checksum(zeroedChecksum + opcode  + nseq, len(opcode + zeroedChecksum + nseq), 'sendACK')

        header = (opcode, finalChecksum, nseq)

        # fixed chunksize (4096 bytes)
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
            
    def upload(self, filesize, fileName, originalMd5):
        fileName = fileName.rstrip('\x00')
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

        self.stopFileTransfer(totalPackets+1, fileName, originalMd5)

        bytesInLatestPacket = filesize % CHUNKSIZE
        Logger.LogWarning(f"There are {bytesInLatestPacket} bytes on the las packet. removing padding")
        file[len(file)-1] = file[len(file)-1][0:bytesInLatestPacket]
        Logger.LogWarning(f"Padding removed")
        self.saveFile(file, fileName)

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
        opcode = bytes([ACK_OPCODE])
        zeroedChecksum = (0).to_bytes(4, BYTEORDER)
        nseqToBytes = nseq.to_bytes(4, BYTEORDER)
        finalChecksum = Checksum.get_checksum(zeroedChecksum + opcode  + nseqToBytes, len(opcode + zeroedChecksum + nseqToBytes), 'sendACK')
        header = (opcode, finalChecksum, nseqToBytes)
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
        
        Logger.LogInfo('######################')
        Logger.LogInfo('El archivo se ha subido al servidor! ')
        Logger.LogInfo('######################')
                

    def saveFile(self, file, fileName):
        completeName = os.path.join(self.storage, fileName)
        os.makedirs(os.path.dirname(completeName), exist_ok=True)
        
        fileWriter = open(completeName, "wb")
        for i in range(0, len(file)):
            fileWriter.write(file[i])
        
        Logger.LogInfo(f"File written into: {completeName}")
        fileWriter.close()

    def isChecksumOK(self, header, payload):
        opcode = header['opcode'].to_bytes(1, BYTEORDER)
        checksum = (header['checksum']).to_bytes(4, BYTEORDER)
        nseqToBytes = header['nseq'].to_bytes(4, BYTEORDER)
        
        return Checksum.is_checksum_valid(checksum + opcode + nseqToBytes, len(opcode + checksum + nseqToBytes))
    
    def stopFileTransfer(self, nseq, fileName, originalMd5):
        opcode = bytes([STOP_FILE_TRANSFER_OPCODE])
        zeroedChecksum = (0).to_bytes(4, BYTEORDER)
        nseqToBytes = nseq.to_bytes(4, BYTEORDER)
        finalChecksum = Checksum.get_checksum(zeroedChecksum + opcode  + nseqToBytes, len(opcode + zeroedChecksum + nseqToBytes), 'sendACK')
        header = (opcode, finalChecksum, nseqToBytes)
        
        file:bytes
        completeName = os.path.join(self.storage, fileName)
        with open(completeName, 'rb') as file:
            file = file.read()

        md5 = hashlib.md5(file)
        Logger.LogDebug(f"File server MD5: \t{md5.hexdigest()}")
        Logger.LogDebug(f"Client's MD5: \t\t{originalMd5.hex()}")        
        
        state = bytes([STATE_ERROR]) # Not okay by default
        if md5.hexdigest() == originalMd5.hex():
            state = bytes([STATE_OK])

        payload = (md5.digest(), state)
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
