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
        """
            Mandar mensaje inicial
        """
        self.sendUploadRequest(filename)
        self.receiveFileTransferTypeResponse()

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

        # while no termine de enviar paquetes 
        #     lleno la window
        #     envio todo
        #     espero acks
        #     marco en la cola que me llego 
        #     if es el primero en la cola
        #        dropeo n paquetes

        # VER COMO LO CONSEGUIMOS XD
        filesize = 4096*31
        totalPackets = filesize / CHUNKSIZE
        packetsACKed = 0
        packetsPushed = 0
        nseq = 1
        payloadWithNseq = {}

        while packetsACKed != totalPackets:
            while ( (len(self.window) != 10) and (packetsPushed != totalPackets)):
                payloadAux = archivo[packetsPushed * CHUNKSIZE : (packetsPushed + 1) * CHUNKSIZE]
                payloadWithNseq[nseq] = payloadAux
                self.window.append({'nseq': nseq, 'isSent': False, 'isACKed': False})
                packetsPushed += 1
                nseq += 1
            
            for packet in self.window:
                if not packet['isSent']:
                    self.sendPackage(payloadWithNseq[packet['nseq']], packet['nseq'])
                    packet['isSent'] = True
            
            ackReceived = self.receiveACK()

            for packet in self.window:
                if ackReceived == packet['nseq']:
                    packet['isACKed'] = True
                    packetsACKed += 1

            
            if self.window[0]['isACKed']:
                self.moveWindow()

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
       self.send(message)

    def receiveACK(self):
        received_message, (serverAddres, serverPort) = self.socket.receive(ACK_SIZE)

        header = Packet.unpack_ack(received_message)

        return header['nseq']

    def moveWindow(self):
        while len(self.window) != 0 and self.window[0]['isACKed']:
            self.window.pop(0)

    def download(self, filename):
        pass

