from common.Packet import Packet
from common.Utils import Utils
from common.constants import *

class ServerSelectiveRepeat:

    def __init__(self, socket, clientAddress, clientPort):
        self.socket = socket
        self.clientAddress = clientAddress
        self.clientPort = clientPort
        self.protocolID = bytes([0x1])

    def send(self, message):
        self.socket.send(message, self.clientAddress, self.clientPort)

    def sendFileTransferTypeResponse(self):
        opcode = bytes([0x0])
        checksum = (2).to_bytes(1, BYTEORDER)
        nseq = (0).to_bytes(1, BYTEORDER)
        header = (opcode, checksum, nseq)

        # chunksize fijo (4096 bytes)
        chunksize = CHUNKSIZE.to_bytes(4, BYTEORDER)

        message = Packet.pack_file_transfer_type_response(header, chunksize)
        self.send(message)

    def upload(self, filename):
        pass

    def download(self, filename):
        pass

