import hashlib
import math
import time
import os
from common.Packet import Packet
from common.Utils import Utils
from common.constants import *
from common.Logger import *
from common.Checksum import *

class ClientSelectiveRepeat:

    def __init__(self):
        self.serverAddress = None
        self.serverPort = None
        self.socket = None
        self.protocolID = bytes([0x1])
        self.window = []
        self.chunksize = None
        self.storage = None
  
    def setServerInfo(self, serverAddress, serverPort, socket):
        self.serverAddress = serverAddress
        self.serverPort = serverPort
        self.socket = socket

    def setStorage(self, storage):
        self.storage = storage
    
    def send(self, message):
        self.socket.send(message, self.serverAddress, self.serverPort)
        
    def upload(self, filename):
        Logger.LogInfo (f"About to start uploading: {filename}")
        self.window = []
        initCommunicationSocketTimeout = 0
        communicationStarted = False
        
        file:bytes        
        with open(filename, 'rb') as file:
            file = file.read()
            
        md5 = hashlib.md5(file)
        filesize = len(file)
        totalPackets = math.ceil(filesize / CHUNKSIZE)
        
        Logger.LogInfo(f"File: {filename} - Size: {filesize} - md5: {md5.hexdigest()} - Packets to send: {totalPackets}")
        
        self.sendUploadRequest(filename, filesize, md5.digest())
        firstPacketSentTime = time.time()

        while (not communicationStarted) and (initCommunicationSocketTimeout < CLIENT_SOCKET_TIMEOUTS):
            try:
                self.socket.settimeout(0.2)
                self.receiveFileTransferTypeResponse()
                initCommunicationSocketTimeout = 0
                communicationStarted = True
            except TimeoutError:                
                initCommunicationSocketTimeout += 1
                Logger.LogWarning(f"There has been a timeout (timeout number: {initCommunicationSocketTimeout})")

            if (not communicationStarted) and (time.time() - firstPacketSentTime > SELECTIVE_REPEAT_PACKET_TIMEOUT):
                self.sendUploadRequest(filename, filesize, md5.digest())
                firstPacketSentTime = time.time()

        Logger.LogInfo(f"Total de paquetes a enviar {totalPackets}")
        packetsACKed = 0
        packetsPushed = 0
        nseq = 1
        payloadWithNseq = {}
        socketTimeouts = 0

        while (packetsACKed != totalPackets) and (socketTimeouts < CLIENT_SOCKET_TIMEOUTS):
            while ( (len(self.window) != 10) and (packetsPushed != totalPackets)):
                payloadAux = file[packetsPushed * CHUNKSIZE : (packetsPushed + 1) * CHUNKSIZE]
                payloadWithNseq[nseq] = payloadAux
                self.window.append({'nseq': nseq, 'isSent': False, 'isACKed': False, 'sentAt': None})                
                packetsPushed += 1
                nseq += 1
            
            for e in self.window:
                if not e['isSent']:
                    Logger.LogDebug(f"Sending packet with sequence: {e['nseq']}")
                    self.sendPackage(payloadWithNseq[e['nseq']], e['nseq'])
                    e['sentAt'] = time.time()
                    e['isSent'] = True
            
            ackReceived = None

            try:
                self.socket.settimeout(0.2)
                ackReceived = self.receiveACK()
                socketTimeouts = 0
            except TimeoutError:                
                socketTimeouts += 1
                Logger.LogWarning(f"There has been a socket timeout (number: {socketTimeouts})")
            except:
                Logger.LogError("There has been an error receiving the ACK")

            for e in self.window:
                if (not e['isACKed']) and ackReceived == e['nseq']:
                    e['isACKed'] = True
                    packetsACKed += 1
                    Logger.LogDebug(f"ACKed {packetsACKed} packets")  
                if (not e['isACKed']) and (time.time() - e['sentAt'] > SELECTIVE_REPEAT_PACKET_TIMEOUT):
                    if (e['nseq'] != totalPackets):
                        self.sendPackage(payloadWithNseq[e['nseq']], e['nseq'])
                    else:
                        self.sendLastPackage(payloadWithNseq[e['nseq']], e['nseq'])
                    e['sentAt'] = time.time()
            
            if self.window[0]['isACKed']:
                Logger.LogDebug("Moving window")
                self.moveSendWindow()


        self.stopUploading(int(totalPackets + 1))

        print('File transfer has ended.')
        Logger.LogInfo(f"Total packets to send: {totalPackets}, nseq: {nseq}, socket timeouts: {socketTimeouts}")

    def sendUploadRequest(self, fileName, fileSize, md5):
        opcode = bytes([0x0])
        zeroedChecksum = (0).to_bytes(4, BYTEORDER)
        nseq = (0).to_bytes(1, BYTEORDER)
        finalChecksum = Checksum.get_checksum(zeroedChecksum + opcode  + nseq, len(opcode + zeroedChecksum + nseq), 'sendUploadRequest')
        header = (opcode, finalChecksum, nseq)

        protocol = self.protocolID
        fileName = fileName.encode()
        payload  = (protocol, fileName,(fileSize).to_bytes(16, BYTEORDER), md5)

        message = Packet.pack_upload_request(header, payload)
        self.send(message)

    def receiveFileTransferTypeResponse(self):
        received_message, (udpServerThreadAddress, udpServerThreadPort) = self.socket.receive(FILE_TRANSFER_TYPE_RESPONSE_SIZE)

        self.serverAddress = udpServerThreadAddress
        self.serverPort = udpServerThreadPort

        header, payload = Packet.unpack_file_transfer_type_response(received_message)
        self.chunksize = payload['chunksize']
        
    def sendPackage(self, payload, nseq):
        opcode = bytes([0x4])
        zeroedChecksum = (0).to_bytes(4, BYTEORDER)
        nseqToBytes = (nseq).to_bytes(4, BYTEORDER)

        # Checksum has to go first, for alignment and calculation
        finalChecksum = Checksum.get_checksum(zeroedChecksum + opcode  + nseqToBytes, len(opcode + zeroedChecksum + nseqToBytes), 'sendPackage')

        header = (opcode, finalChecksum, nseqToBytes)
        message = Packet.pack_package(header, payload)
        Logger.LogInfo(f"About to send packet nseq: {nseq}")
        self.send(message)
        
    def receiveACK(self):
        received_message, (serverAddres, serverPort) = self.socket.receive(ACK_SIZE)

        header = Packet.unpack_ack(received_message)
        Logger.LogInfo(f"RECEIVED ACK. \t{header}")
        opcode = header['opcode'].to_bytes(1, BYTEORDER)
        checksum = (header['checksum']).to_bytes(4, BYTEORDER)
        nseqToBytes = header['nseq'].to_bytes(4, BYTEORDER)
        
        if Checksum.is_checksum_valid(checksum + opcode + nseqToBytes, len(opcode + checksum + nseqToBytes)):
            return header['nseq']
        else:
            Logger.LogWarning("Invalid checksum for ACK receeived")
            return header['nseq']

    def moveSendWindow(self):
        while len(self.window) != 0 and self.window[0]['isACKed']:
            self.window.pop(0)

    def stopUploading(self, nseq):
        self.socket.settimeout(None)
        received_message, (serverAddres, serverPort) = self.socket.receive(STOP_FILE_TRANSFER_SIZE)

        header, payload = Packet.unpack_stop_file_transfer(received_message)

        if payload["state"] == 0:
            Logger.LogError("There's been an error uploading the file in the server. File corrupt in the server")

        opcode = bytes([0x7])
        zeroedChecksum = (0).to_bytes(4, BYTEORDER)
        nseqToBytes = (header['nseq']).to_bytes(4, BYTEORDER)
        finalChecksum = Checksum.get_checksum(zeroedChecksum + opcode  + nseqToBytes, len(opcode + zeroedChecksum + nseqToBytes), 'stopUploading')
        header = (opcode, finalChecksum, nseqToBytes)

        message = Packet.pack_ack(header)
        
        self.send(message)

        print('Finalized uploading file')

    def sendLastPackage(self, payload, nseq):
        opcode = bytes([0x4])

        checksum = (2).to_bytes(4, BYTEORDER)
           
        nseqToBytes = nseq.to_bytes(4, BYTEORDER)
        header = (opcode, checksum, nseqToBytes)

        message = Packet.pack_package(header, payload)
        self.send(message)

    def download(self, filename):
        Logger.LogInfo (f"About to start downloading: {filename}")
        self.window = []
        initCommunicationSocketTimeout = 0
        communicationStarted = False
           
        self.sendDownloadRequest(filename)
        firstPacketSentTime = time.time()

        filesize = None
        md5 = None

        while (not communicationStarted) and (initCommunicationSocketTimeout < CLIENT_SOCKET_TIMEOUTS):
            try:
                self.socket.settimeout(0.2)
                filesize, md5 = self.receiveDownloadResponse()
                initCommunicationSocketTimeout = 0
                communicationStarted = True
            except TimeoutError:                
                initCommunicationSocketTimeout += 1
                Logger.LogWarning(f"There has been a timeout (timeout number: {initCommunicationSocketTimeout})")

            if (not communicationStarted) and (time.time() - firstPacketSentTime > SELECTIVE_REPEAT_PACKET_TIMEOUT):
                self.sendDownloadRequest(filename)
                firstPacketSentTime = time.time()

        Logger.LogDebug(f"You are about to download a file of {filesize} bytes and with an md5 of {md5}")

        # POLITICA DE REINTENTOS #
        self.sendConnectionACK()

        fileNameModified = filename.rstrip('\x00')
        file = {}
        totalPackets = math.ceil(filesize / CHUNKSIZE)
        distinctAcksSent = 0
        firstIteration = True

        for i in range(1,10):
            self.window.append({'nseq': i, 'isACKSent': False})

        header = None
        payload = None

        while distinctAcksSent != totalPackets:
            if not firstIteration:
                header, payload = self.receivePackage()
            else:
                firstIteration = False

            if header != None and self.isChecksumOK(header, payload):
                self.sendACK(header['nseq'])
            
            for e in self.window:
                if header != None and (not e['isACKSent']) and header['nseq'] == e['nseq']:
                    e['isACKSent'] = True
                    distinctAcksSent += 1
                    file[header['nseq'] - 1] = payload
                  
            if header != None and header['nseq'] == self.window[0]['nseq']:
                self.moveReceiveWindow()

        bytesInLatestPacket = filesize % CHUNKSIZE
        Logger.LogWarning(f"There are {bytesInLatestPacket} bytes on the las packet. removing padding")
        file[len(file)-1] = file[len(file)-1][0:bytesInLatestPacket]
        Logger.LogWarning(f"Padding removed")
        self.saveFile(file, fileNameModified)

        self.stopFileTransfer(totalPackets+1, fileNameModified, md5)

        print('File transfer has ended.')

    def sendDownloadRequest(self, fileName):
        opcode = bytes([0x2])
        zeroedChecksum = (0).to_bytes(4, BYTEORDER)
        nseq = (0).to_bytes(1, BYTEORDER)
        finalChecksum = Checksum.get_checksum(zeroedChecksum + opcode  + nseq, len(opcode + zeroedChecksum + nseq), 'sendDownloadRequest')
        header = (opcode, finalChecksum, nseq)
    
        protocol = self.protocolID
        fileName = fileName.encode()
        payload  = (protocol, fileName)
    
        message = Packet.pack_download_request(header, payload)
        self.send(message)

    def receiveDownloadResponse(self):
        received_message, (udpServerThreadAddress, udpServerThreadPort) = self.socket.receive(DOWNLOAD_RESPONSE_SIZE)

        self.serverAddress = udpServerThreadAddress
        self.serverPort = udpServerThreadPort

        header, payload = Packet.unpack_download_response(received_message)

        return payload['filesize'], payload['md5']
    
    def receivePackage(self):
        received_message, (serverAddres, serverPort) = self.socket.receive(PACKET_SIZE)

        if Utils.bytesToInt(received_message[:1]) == 0:
            header, payload = Packet.unpack_upload_request(received_message)
        else:
            header, payload = Packet.unpack_package(received_message)

        return header, payload
    
    def moveReceiveWindow(self):
        while len(self.window) != 0 and self.window[0]['isACKSent']:
            lastNseq = self.window[-1]['nseq']
            self.window.pop(0)
            self.window.append({'nseq': lastNseq + 1, 'isACKSent': False})

    def isChecksumOK(self, header, payload):
        opcode = header['opcode'].to_bytes(1, BYTEORDER)
        checksum = (header['checksum']).to_bytes(4, BYTEORDER)
        nseqToBytes = header['nseq'].to_bytes(4, BYTEORDER)
        
        return Checksum.is_checksum_valid(checksum + opcode + nseqToBytes, len(opcode + checksum + nseqToBytes))
    
    def sendACK(self, nseq):
        opcode = bytes([0x5])
        zeroedChecksum = (0).to_bytes(4, BYTEORDER)
        nseqToBytes = nseq.to_bytes(4, BYTEORDER)
        finalChecksum = Checksum.get_checksum(zeroedChecksum + opcode  + nseqToBytes, len(opcode + zeroedChecksum + nseqToBytes), 'sendACK')
        header = (opcode, finalChecksum, nseqToBytes)
        message = Packet.pack_ack(header)
        Logger.LogInfo(f"Sending ACK {nseq} ")
        self.send(message)

    def sendConnectionACK(self):
        opcode = bytes([0x3])
        zeroedChecksum = (0).to_bytes(4, BYTEORDER)
        nseqToBytes = (0).to_bytes(4, BYTEORDER)
        finalChecksum = Checksum.get_checksum(zeroedChecksum + opcode  + nseqToBytes, len(opcode + zeroedChecksum + nseqToBytes), 'sendACK')
        header = (opcode, finalChecksum, nseqToBytes)
        message = Packet.pack_ack(header)
        Logger.LogInfo(f"Sending Connection ACK")
        self.send(message)

    def saveFile(self, file, fileName):
        completeName = os.path.join(self.storage, fileName)
        os.makedirs(os.path.dirname(completeName), exist_ok=True)
        
        fileWriter = open(completeName, "wb")
        for i in range(0, len(file)):
            fileWriter.write(file[i])
        
        Logger.LogInfo(f"File written into: {completeName}")
        fileWriter.close()

    def stopFileTransfer(self, nseq, fileName, originalMd5):
        opcode = bytes([0x6])
        zeroedChecksum = (0).to_bytes(4, BYTEORDER)
        nseqToBytes = nseq.to_bytes(4, BYTEORDER)
        finalChecksum = Checksum.get_checksum(zeroedChecksum + opcode  + nseqToBytes, len(opcode + zeroedChecksum + nseqToBytes), 'sendACK')
        header = (opcode, finalChecksum, nseqToBytes)
        
        file:bytes
        completeName = os.path.join(self.storage, fileName)
        with open(completeName, 'rb') as file:
            file = file.read()

        md5 = hashlib.md5(file)
        Logger.LogDebug(f"File client MD5: \t{md5.hexdigest()}")
        Logger.LogDebug(f"Server's MD5: \t\t{originalMd5.hex()}")        
        
        state = bytes([0x0]) # Not okay by default
        if md5.hexdigest() == originalMd5.hex():
            state = bytes([0x1])

        payload = (md5.digest(), state)
        message = Packet.pack_stop_file_transfer(header, payload)
    
        self.send(message)
        