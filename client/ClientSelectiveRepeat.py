from tqdm import tqdm
import time
import hashlib
import math
import time
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
  
    def setServerInfo(self, serverAddress, serverPort, socket):
        self.serverAddress = serverAddress
        self.serverPort = serverPort
        self.socket = socket

    def send(self, message):
        self.socket.send(message, self.serverAddress, self.serverPort)
        
    def upload(self, filename):
        Logger.LogInfo (f"About to start uploading: {filename}")
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
            for i in tqdm (range (totalPackets),desc="Uploading...",ascii=False, ncols=75):
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
                    self.moveWindow()

        print("Verifying file...")
        self.stopUploading(int(totalPackets + 1))

        print('File transfer has completed.')
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

    def moveWindow(self):
        while len(self.window) != 0 and self.window[0]['isACKed']:
            self.window.pop(0)

    def stopUploading(self, nseq):
        self.socket.settimeout(None)
        received_message, (serverAddres, serverPort) = self.socket.receive(STOP_FILE_TRANSFER_SIZE)

        header, payload = Packet.unpack_stop_file_transfer(received_message)
        Logger.LogInfo(f"Received ACK: {header['nseq']}")

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
        pass