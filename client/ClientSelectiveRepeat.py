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
        self.retries = False
  
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
                if (not e['isACKed']) and (time.time() - e['sentAt'] > 2):
                    print('--- TIMEOUT Y RETRANSMISION DEL PACKET:', e['nseq'], '---')
                    self.sendPackage(payloadWithNseq[e['nseq']], e['nseq'])
                    e['sentAt'] = time.time()
            
            if self.window[0]['isACKed']:
                self.moveWindow()

        print('packetsACKed: ', packetsACKed, 'socketTimeouts: ', socketTimeouts)

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
        if nseq == 10 and not self.retries:
            checksum = (0).to_bytes(4, BYTEORDER)
            self.retries = True
           
        nseqToBytes = nseq.to_bytes(4, BYTEORDER)
        header = (opcode, checksum, nseqToBytes)

        message = Packet.pack_package(header, payload)
        self.send(message)
        print('Envié el paquete con nseq: ', nseq)

    def receiveACK(self):
        received_message, (serverAddres, serverPort) = self.socket.receive(ACK_SIZE)

        header = Packet.unpack_ack(received_message)
        print('Recibi el ack: ', header['nseq'])
        return header['nseq']

    def moveWindow(self):
        while len(self.window) != 0 and self.window[0]['isACKed']:
            self.window.pop(0)

    def download(self, filename):
        pass