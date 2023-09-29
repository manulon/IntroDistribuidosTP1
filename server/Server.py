from socket import *
from common.Socket import Socket
from common.Packet import Packet
from common.constants import *
from server.ServerSelectiveRepeat import *
from server.ServerStopAndWait import *

class Server():
    MAX_FILE_SIZE = 4000000000 # 4GB

    def __init__(self, address, port):
        self.port = port
        self.address = address
        self.socket = Socket(self.port, self.address)
        self.protocol = None

    def send(self, message):
        self.socket.send(message, self.clientAddress, self.clientPort)

    def receive(self):
        print('The server is ready to receive')
        while True:
            received_message, (clientAddress, clientPort) = self.socket.receive(FILE_TRANSFER_REQUEST_SIZE)
            opcode = int.from_bytes(received_message[:1], BYTEORDER)
            match opcode:
                case 0: # Upload
                    header, payload = Packet.unpack_upload_request(received_message)
                    if payload['fileSize'] > self.MAX_FILE_SIZE:
                        self.sendFileTooBigError()
                        break
                    if Utils.getFreeDiskSpace() <= payload['fileSize']:
                        self.sendNoDiskSpaceError()
                        break
                    #if self.fileExists(payload['fileName']):
                    #    self.sendFileAlreadyExistsResponse()
                    #    break
                    if payload['protocol'] == 1:
                        print('Selected Selective Repeat')
                        protocol = ServerSelectiveRepeat(self.socket, clientAddress, clientPort)
                        self.protocol = protocol
                        self.protocol.sendFileTransferTypeResponse()
                        self.protocol.upload(payload['fileSize'])
                    else:
                        print('Selected Stop and Wait')
                        protocol = ServerStopAndWait(self.socket, clientAddress, clientPort)
                        self.protocol = protocol
                        self.protocol.sendFileTransferTypeResponse()
                        self.protocol.upload(payload['fileSize'])
                    break
                case 2: # Download
                    #print('downloading (stop and wait): '+ str(message))
                    #StopAndWait.download()
                    break
                case 7: # List
                    #StopAndWait.list(message)
                    break
                case default:
                    # print("message not understood")
                    # close connection
                    break
            #modifiedMessage = message.decode().upper()

    def sendFileTooBigError(self):
        opcode = (FILE_TOO_BIG_OPCODE).to_bytes(1, BYTEORDER)
        checksum = (2).to_bytes(4, BYTEORDER)
        nseq = (0).to_bytes(4, BYTEORDER)
        header = (opcode, checksum, nseq)

        message = Packet.pack_file_too_big_error(header)
        self.send(message)

    def sendFileAlreadyExistsError(self):
        opcode = (FILE_ALREADY_EXISTS_OPCODE).to_bytes(1, BYTEORDER)
        checksum = (2).to_bytes(4, BYTEORDER)
        nseq = (0).to_bytes(4, BYTEORDER)
        header = (opcode, checksum, nseq)

        message = Packet.pack_file_already_exists_error(header)
        self.send(message)

    def sendNoDiskSpaceError(self):
        opcode = (NO_DISK_SPACE_OPCODE).to_bytes(1, BYTEORDER)
        checksum = (2).to_bytes(4, BYTEORDER)
        nseq = (0).to_bytes(4, BYTEORDER)
        header = (opcode, checksum, nseq)

        message = Packet.pack_no_disk_space_error(header)
        self.send(message)
    '''
    def sendFileDoesNotExistError(self):
        opcode = (FILE_DOES_NOT_EXIST_OPCODE).to_bytes(1, BYTEORDER)
        checksum = (2).to_bytes(4, BYTEORDER)
        nseq = (0).to_bytes(4, BYTEORDER)
        header = (opcode, checksum, nseq)

        message = Packet.pack_file_does_not_exist_error(header)
        self.send(message)
    '''

    def close(self):
        self.socket.close()
