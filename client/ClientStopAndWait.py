from common.Packet import Packet
from common.Utils import Utils
from common.constants import *

class ClientStopAndWait:
    def __init__(self):
        self.serverAddress = None
        self.serverPort = None
        self.socket = None
        self.protocolID = bytes([0x2])

    def upload(self, filename):
        """
            Mandar mensaje inicial
        """
        self.uploadRequest(filename)
        chunksize = self.receiveFileTransferTypeResponse()
        if chunksize == ERROR_CODE:
            return
        self.sendFile(filename, chunksize)
        # TODO: Esto es lo que tenian antes usted:
        """ 
            Mandar mensaje inicial
            Esperar al ACK con chunksize 
            Particionar archivo en segmentos de chunksize
            Mientras(queden segmentos sin enviar)
                Mandar segmento N
                Esperar ACK del Segmento N
                if(N es ultimo)
                    
                N+1
        
        # checksum = Hasher.checksum(package)
        checksum = 0
        file_size = os.stat(filename).st_size
        with open(filename, 'rb') as f:
            read_bytes = f.read()
            md5_encoding = Hasher.md5(read_bytes)
            message = Packet.pack_upload_request(checksum, 0, filename, file_size, md5_encoding)
            self.client.send(message)
        """

    def uploadRequest(self, fileName):
        opcode = bytes([0x0])
        checksum = (2).to_bytes(4, BYTEORDER)
        nseq = (3).to_bytes(1, BYTEORDER)
        header = (opcode, checksum, nseq)

        protocol = self.protocolID
        fileName = fileName.encode()
        fileSize = Utils.bytes(16)  # 16 bytes vacíos
        md5 = Utils.bytes(16)  # 16 bytes vacíos
        payload = (protocol, fileName, fileSize, md5)

        message = Packet.pack_upload_request(header, payload)
        self.send(message)

    def receiveFileTransferTypeResponse(self):
        received_message, _ = self.socket.receive(FILE_TRANSFER_TYPE_RESPONSE_SIZE)
        opcode = int.from_bytes(received_message[:1], BYTEORDER)
        
        if opcode == FILE_TRANSFER_RESPONSE_OPCODE:
            header, payload = Packet.unpack_file_transfer_type_response(received_message)
            return payload['chunksize']
        else:
            if opcode == FILE_NO_DISK_SPACE_OPCODE:
                print('Not enough disk space in server to upload file')
            elif opcode == FILE_TOO_BIG_OPCODE:
                print('File too big, not supported by protocol')
            elif opcode == FILE_ALREADY_EXISTS_OPCODE:
                print('The file that is trying to upload already exists in the server')
            else:
                print('Uknown error, retry')
            return ERROR_CODE
    
        '''
        header, payload = Packet.unpack_file_transfer_type_response(received_message)
        print('----------')
        print('Recibi este header:', header)
        print('El tamaño del chunk es:', payload)
        print('¡Adios!')
        '''

    def send_file(self, filename, chunksize):
        mockFile = b''
        numberOfPackets = 31
        for i in range(numberOfPackets):
            mockFile += Utils.bytesNumerados(chunksize, i)
        
        filesize = 4096*31
        totalPackets = filesize / chunksize
        packetsPushed = 0

        while (packetsPushed < totalPackets):
            sequenceNumber = (packetsPushed + 1) % 2 # starts in 1
            payload = mockFile[packetsPushed * CHUNKSIZE : (packetsPushed + 1) * CHUNKSIZE]
            self.sendPacket(sequenceNumber, payload)
            ackNseq = self.receiveACK()
            if (ackNseq == sequenceNumber):
                packetsPushed += 1
            else:
                while(ackNseq != sequenceNumber): # case 4
                    self.sendPacket(sequenceNumber,payload)
                    ackNseq = self.receiveACK()
                
        
    def sendPacket(self, nseq, payload):
        opcode = bytes([0x4])
        checksum = (2).to_bytes(4, BYTEORDER)
        nseqToBytes = nseq.to_bytes(4, BYTEORDER)
        header = (opcode, checksum, nseqToBytes)

        message = Packet.pack_package(header, payload)
        self.send(message)

    def setServerInfo(self, serverAddress, serverPort, socket):
        self.serverAddress = serverAddress
        self.serverPort = serverPort
        self.socket = socket
        
    def send(self, message):
        self.socket.send(message, self.serverAddress, self.serverPort)

    def receiveACK(self):
        # timeout?
        received_message, _ = self.socket.receive(ACK_SIZE)
        header = Packet.unpack_ack(received_message)
        return header['nseq']


    def download(self, filename):
        pass


