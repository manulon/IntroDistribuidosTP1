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
        checksum = (2).to_bytes(1, BYTEORDER)
        nseq = (3).to_bytes(1, BYTEORDER)
        header = (opcode, checksum, nseq)

        protocol = self.protocolID
        fileName = fileName.encode()
        fileSize = Utils.bytes(16)  # 16 bytes vacíos
        md5 = Utils.bytes(16)  # 16 bytes vacíos
        payload = (protocol, fileName, fileSize, md5)

        message = Packet.pack_upload_request(header, payload)
        self.send(message)

    def setServerInfo(self, serverAddress, serverPort, socket):
        self.serverAddress = serverAddress
        self.serverPort = serverPort
        self.socket = socket
        
    def send(self, message):
        self.socket.send(message, self.serverAddress, self.serverPort)
        modifiedMessage, serverAddress = self.socket.receive()
        print(modifiedMessage.decode())

    def download(self, filename):
        pass