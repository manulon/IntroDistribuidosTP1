import hashlib
import os
import time
from common.Logger import *
from common.Checksum import *
from common.Packet import Packet
import common.constants as const

class ServerStopAndWait:

    def __init__(self, socket, clientAddress, clientPort, storage):
        self.socket = socket
        self.clientAddress = clientAddress
        self.clientPort = clientPort
        self.protocolID = bytes([const.STOP_AND_WAIT])
        self.storage = storage

    def send(self, message):
        self.socket.send(message, self.clientAddress, self.clientPort)

    def sendFileTransferTypeResponse(self, fileSize):
        opcode = bytes([const.FILE_TRANSFER_RESPONSE_OPCODE])
        zeroedChecksum = (0).to_bytes(4, const.BYTEORDER)
        nseq = (0).to_bytes(4, const.BYTEORDER)
        finalChecksum = Checksum.get_checksum(zeroedChecksum + opcode  + nseq, len(opcode + zeroedChecksum + nseq), 'sendACK')
        header = (opcode, finalChecksum, nseq)

        # fixed chunksize (4096 bytes)
        chunksize = const.CHUNKSIZE.to_bytes(4, const.BYTEORDER)

        message = Packet.pack_file_transfer_type_response(header, chunksize)
        self.send(message)

    def upload(self, fileSize, fileName, originalMd5):
        fileName = fileName.rstrip('\x00')
        self.sendFileTransferTypeResponse(fileSize)
        totalPackets = fileSize / const.CHUNKSIZE
        acksSent = 0
        nextNseq = 1
        file = []

        while acksSent < totalPackets:
            header, payload = self.receivePackage()
            if header['nseq'] == nextNseq:
                #package = Packet.pack_package(header, payload)
                #if self.isChecksumOK(header, payload):
                self.sendACK(header['nseq'])
                file.append(payload)
                nextNseq = acksSent % 2
                acksSent += 1
                #else:
                #    Logger.LogError('Checksum error') # client resends packet (corrupted packet)
            else: # client resends packet - cases 3 (lost ACK) and 4 (timeout)
                self.sendACK(header['nseq']) # server only resends ACK (detects duplicate)

        bytesInLatestPacket = fileSize % const.CHUNKSIZE
        Logger.LogWarning(f"There are {bytesInLatestPacket} bytes on the las packet. removing padding")
        file[len(file)-1] = file[len(file)-1][0:bytesInLatestPacket]
        Logger.LogWarning(f"Padding removed")

        #if state == STATE_OK:
        self.saveFile(file, fileName)
        md5, state = self.checkFileMD5(fileName, originalMd5)
        self.stopFileTransfer(nextNseq, fileName, md5, state)
        #self.showFileAsBytes(file)

    def download(self, filename):
        pass

    def receivePackage(self):
        received_message, (serverAddres, serverPort) = self.socket.receive(const.PACKET_SIZE)
        header, payload = Packet.unpack_package(received_message)
        return header, payload
    
    def sendACK(self, nseq):
        opcode = bytes([const.ACK_OPCODE])
        checksum = (2).to_bytes(4, const.BYTEORDER)
        nseqToBytes = nseq.to_bytes(4, const.BYTEORDER)
        header = (opcode, checksum, nseqToBytes)

        message = Packet.pack_ack(header)
        self.send(message)

    def saveFile(self, file, fileName):
        completeName = os.path.join(self.storage, fileName)
        os.makedirs(os.path.dirname(completeName), exist_ok=True)
        
        fileWriter = open(completeName, "wb")
        for i in range(0, len(file)):
            fileWriter.write(file[i])
        
        Logger.LogInfo(f"File written into: {completeName}")
        fileWriter.close()

    def isChecksumOK(self, header, payload):
        opcode = header['opcode'].to_bytes(1, const.BYTEORDER)
        checksum = (header['checksum']).to_bytes(4, const.BYTEORDER)
        nseqToBytes = header['nseq'].to_bytes(4, const.BYTEORDER)
        
        return Checksum.is_checksum_valid(checksum + opcode + nseqToBytes + payload, len(opcode + checksum + nseqToBytes + payload))

    def stopFileTransfer(self, nseq, fileName, md5, state):
        opcode = bytes([const.STOP_FILE_TRANSFER_OPCODE])
        zeroedChecksum = (0).to_bytes(4, const.BYTEORDER)
        nseqToBytes = nseq.to_bytes(4, const.BYTEORDER)
        finalChecksum = Checksum.get_checksum(zeroedChecksum + opcode  + nseqToBytes, len(opcode + zeroedChecksum + nseqToBytes), 'sendACK')
        header = (opcode, finalChecksum, nseqToBytes)
        
        #file:bytes
        #completeName = os.path.join(self.storage, fileName)
        #with open(completeName, 'rb') as file:
        #    file = file.read()

        payload = (md5.digest(), state)
        message = Packet.pack_stop_file_transfer(header, payload)
    
        self.send(message)
        stopFileTransferMsgSentAt = time.time()

        communicationFinished = False
        stopCommunicationSocketTimeout = 0

        while (not communicationFinished) and (stopCommunicationSocketTimeout < const.LAST_ACK_PACKET_TIMEOUT):
           try:
               self.socket.settimeout(0.2)
               received_message, (serverAddres, serverPort) = self.socket.receive(const.ACK_SIZE)
               stopCommunicationSocketTimeout = 0
               communicationFinished = True
           except TimeoutError:
               # Acá se da por sentado que el cliente se cerró
               stopCommunicationSocketTimeout += 1

           if (not communicationFinished) and (time.time() - stopFileTransferMsgSentAt > const.SELECTIVE_REPEAT_PACKET_TIMEOUT):
                self.send(message)
                stopFileTransferMsgSentAt = time.time()            

    def checkFileMD5(self, fileName, originalMd5):
        file:bytes
        completeName = os.path.join(self.storage, fileName)
        with open(completeName, 'rb') as file:
            file = file.read()

        md5 = hashlib.md5(file)
        Logger.LogDebug(f"File server MD5: \t{md5.hexdigest()}")
        Logger.LogDebug(f"Client's MD5: \t\t{originalMd5.hex()}")        
        
        state = bytes([const.STATE_ERROR]) # Not okay by default
        if md5.hexdigest() == originalMd5.hex():
            state = bytes([const.STATE_OK])
        
        return md5, state

    def showFileAsBytes(self, fileArray):
        content = b''
        for e in fileArray:
            content += e  
        print('######################')
        print('El archivo se ha descargado! Su contenido es el siguiente:')
        print(content)