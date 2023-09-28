from common.Packet import Packet
from common.Utils import Utils
from common.constants import *

class ClientSelectiveRepeat:

    def __init__(self):
        self.serverAddress = None
        self.serverPort = None
        self.socket = None
        self.protocolID = bytes([0x1])

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

    def sendUploadRequest(self, fileName):
        opcode = bytes([0x0])
        checksum = (2).to_bytes(1, BYTEORDER)
        nseq = (0).to_bytes(1, BYTEORDER)
        header = (opcode, checksum, nseq)

        protocol = self.protocolID
        fileName = fileName.encode()
        fileSize = Utils.bytes(16)      # 16 bytes vacíos
        md5      = Utils.bytes(16)      # 16 bytes vacíos
        payload  = (protocol, fileName, fileSize, md5)

        message = Packet.pack_upload_request(header, payload)
        self.send(message)

    def receiveFileTransferTypeResponse(self):
        received_message, (serverAddres, serverPort) = self.socket.receive(FILE_TRANSFER_TYPE_RESPONSE_SIZE)
        
        header, payload = Packet.unpack_file_transfer_type_response(received_message)
        print('----------')
        print('Recibi este header:', header)
        print('El tamaño del chunk es:', payload)
        print('¡Adios!')
        

    def download(self, filename):
        pass

