import math
import time
from common.Packet import Packet
from common.Utils import Utils
from common.constants import *



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
        initCommunicationSocketTimeout = 0
        communicationStarted = False

        self.sendUploadRequest(filename)
        firstPacketSentTime = time.time()

        while (not communicationStarted) and (initCommunicationSocketTimeout < CLIENT_SOCKET_TIMEOUTS):
            try:
                self.socket.settimeout(0.2)
                self.receiveFileTransferTypeResponse()
                initCommunicationSocketTimeout = 0
                communicationStarted = True
            except TimeoutError:
                initCommunicationSocketTimeout += 1

            if (not communicationStarted) and (time.time() - firstPacketSentTime > SELECTIVE_REPEAT_PACKET_TIMEOUT):
                self.sendUploadRequest(filename)
                firstPacketSentTime = time.time()


        #######################################
        #        FAKE STRING BYTES            #
        #######################################
        archivo = b''
        cantidadPaquetes = 31
        for i in range(cantidadPaquetes):
            archivo += Utils.bytesNumerados(self.chunksize, i)
        #######################################
        #        FAKE STRING BYTES            #
        #######################################

        # VER COMO LO CONSEGUIMOS XD
        filesize = 4096*31
        totalPackets = math.ceil(filesize / CHUNKSIZE)
        packetsACKed = 0
        packetsPushed = 0
        nseq = 1
        payloadWithNseq = {}
        socketTimeouts = 0

        while (packetsACKed != totalPackets) and (socketTimeouts < CLIENT_SOCKET_TIMEOUTS):
            while ( (len(self.window) != 10) and (packetsPushed != totalPackets)):
                payloadAux = archivo[packetsPushed * CHUNKSIZE : (packetsPushed + 1) * CHUNKSIZE]
                payloadWithNseq[nseq] = payloadAux
                self.window.append({'nseq': nseq, 'isSent': False, 'isACKed': False, 'sentAt': None})
                packetsPushed += 1
                nseq += 1
            
            for e in self.window:
                if not e['isSent']:
                    self.sendPackage(payloadWithNseq[e['nseq']], e['nseq'])
                    e['sentAt'] = time.time()
                    e['isSent'] = True
            
            try:
                self.socket.settimeout(0.2)
                ackReceived = self.receiveACK()
                socketTimeouts = 0
            except TimeoutError:
                socketTimeouts += 1

            for e in self.window:
                if (not e['isACKed']) and ackReceived == e['nseq']:
                    e['isACKed'] = True
                    packetsACKed += 1  
                if (not e['isACKed']) and (time.time() - e['sentAt'] > SELECTIVE_REPEAT_PACKET_TIMEOUT):
                    self.sendPackage(payloadWithNseq[e['nseq']], e['nseq'])
                    e['sentAt'] = time.time()
            
            if self.window[0]['isACKed']:
                self.moveWindow()


        self.stopUploading(int(totalPackets + 1))

        print('La transferencia ha finalizado')

    def sendUploadRequest(self, fileName):
        opcode = bytes([0x0])
        checksum = (2).to_bytes(4, BYTEORDER)
        nseq = (0).to_bytes(1, BYTEORDER)
        header = (opcode, checksum, nseq)

        protocol = self.protocolID
        fileName = fileName.encode()
        fileSize = (4096*31).to_bytes(16, BYTEORDER)       # 16 bytes 
        md5      = Utils.bytes(16)                         # 16 bytes vacíos
        payload  = (protocol, fileName, fileSize, md5)

        message = Packet.pack_upload_request(header, payload)
        self.send(message)

    def receiveFileTransferTypeResponse(self):
        received_message, (serverAddres, serverPort) = self.socket.receive(FILE_TRANSFER_TYPE_RESPONSE_SIZE)

        header, payload = Packet.unpack_file_transfer_type_response(received_message)

        self.chunksize = payload['chunksize']
        
    def sendPackage(self, payload, nseq):
        opcode = bytes([0x4])

        checksum = (2).to_bytes(4, BYTEORDER)
           
        nseqToBytes = nseq.to_bytes(4, BYTEORDER)
        header = (opcode, checksum, nseqToBytes)

        message = Packet.pack_package(header, payload)
        print('Enviaré un paquete con nseq: ', nseq)
        self.send(message)
        
    def receiveACK(self):
        received_message, (serverAddres, serverPort) = self.socket.receive(ACK_SIZE)

        header = Packet.unpack_ack(received_message)
        print('Recibi el ack: ', header['nseq'])
        return header['nseq']

    def moveWindow(self):
        while len(self.window) != 0 and self.window[0]['isACKed']:
            self.window.pop(0)

    def stopUploading(self, nseq):
        self.socket.settimeout(None)
        received_message, (serverAddres, serverPort) = self.socket.receive(STOP_FILE_TRANSFER_SIZE)

        header, payload = Packet.unpack_stop_file_transfer(received_message)
        print('Recibi el ACK: ', header['nseq'])

        # Aca va la verificacion del md5 del archivo y el state

        opcode = bytes([0x7])
        checksum = (2).to_bytes(4, BYTEORDER)
        nseqToBytes = (header['nseq']).to_bytes(4, BYTEORDER)
        header = (opcode, checksum, nseqToBytes)

        message = Packet.pack_ack(header)
        
        self.send(message)

        print('La carga del archivo ha finalizado, yo ya me cierro. ¡Adios!')

    def download(self, filename):
        pass