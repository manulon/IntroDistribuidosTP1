from socket import *
from common.Socket import Socket
from common.Packet import Packet
from common.constants import *
from common.Utils import *
from server.ServerSelectiveRepeat import ServerSelectiveRepeat
from server.ServerStopAndWait import ServerStopAndWait
from common.Logger import *
from common.Checksum import *
from server.ServerSelectiveRepeat import *

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
            firstPacketIsValid = False
            while not firstPacketIsValid:
                firstPacketIsValid, header, payload, clientAddress, clientPort = self.receiveFirstPacket()
            
            match header['opcode']:
                case 0: # Upload
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
                    Logger.LogError(f"The value {header['opcode']} is not a valid opcode")
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
    def receiveFirstPacket(self):
        received_message, (clientAddress, clientPort) = self.socket.receive(FILE_TRANSFER_REQUEST_SIZE)
        header, payload = Packet.unpack_upload_request(received_message)

        firstPacketIsValid = self.isChecksumOK(header, payload)

        return firstPacketIsValid, header, payload, clientAddress, clientPort

    def isChecksumOK(self, header, payload):
        Logger.LogDebug(f"{header}")
        opcode = header['opcode'].to_bytes(1, BYTEORDER)
        checksum = (header['checksum']).to_bytes(4, BYTEORDER)
        nseqToBytes = header['nseq'].to_bytes(4, BYTEORDER)
        
        return Checksum.is_checksum_valid(checksum + opcode  + nseqToBytes, len(opcode + checksum + nseqToBytes))

    def close(self):
        self.socket.close()
