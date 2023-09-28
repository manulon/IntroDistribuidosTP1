import os

from common.Hasher import Hasher
from common.Packet import Packet
from common.Utils import Utils


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
        modifiedMessage, serverAddress = self.socket.receive()
        print(modifiedMessage.decode())
        
    def upload(self, filename):
        """
            Mandar mensaje inicial
        """
        self.uploadRequest(filename)

    def uploadRequest(self, fileName):
        utils = Utils()
        packet = Packet()
        opcode = bytes([0x0])
        checksum = (2).to_bytes()
        nseq = (3).to_bytes()
        header = (opcode, checksum, nseq)

        protocol = self.protocolID
        fileName = fileName.encode()
        fileSize = utils.bytes(16) # 16 bytes vacíos
        md5 = utils.bytes(16) # 16 bytes vacíos
        payload = (protocol, fileName, fileSize, md5)

        message = packet.pack_upload_request(header, payload)
        self.send(message)

    def download(self, filename):
        pass

