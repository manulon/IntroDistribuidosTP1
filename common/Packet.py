import struct
from common.Utils import Utils
from common.constants import *

class Packet:
    
    @staticmethod
    def pack_upload_request(header, payload):
        opcode = header[0]
        checksum = header[1]
        nseq = header[2]
        protocol = payload[0]
        fileName = payload[1]
        fileSize = payload[2]
        md5 = payload[3]

        return struct.pack(HEADER_FORMAT + UPLOAD_REQUEST_FORMAT, opcode, checksum, nseq, 
                           protocol, fileName, fileSize, md5)

    @staticmethod
    def unpack_upload_request(bytes):
        opcode, checksum, nseq, protocol, fileName, fileSize, md5 = struct.unpack(HEADER_FORMAT + UPLOAD_REQUEST_FORMAT,bytes)
        
        header = {
            'opcode': Utils.bytesToInt(opcode),
            'checksum': Utils.bytesToInt(checksum),
            'nseq': Utils.bytesToInt(nseq)
        }
        payload = {
            'protocol': Utils.bytesToInt(protocol),
            'fileName': fileName.decode(),
            'fileSize': Utils.bytesToInt(fileSize),
            'md5': md5.decode()
        }

        return header, payload
    
    @staticmethod
    def pack_file_transfer_type_response(header, chunksize):
        opcode = header[0]
        checksum = header[1]
        nseq = header[2]
        
        return struct.pack(HEADER_FORMAT + FILE_TRANSFER_TYPE_FORMAT, opcode, checksum, nseq, chunksize)

    @staticmethod
    def unpack_file_transfer_type_response(bytes):
        opcode, checksum, nseq, chunksize = struct.unpack(HEADER_FORMAT + FILE_TRANSFER_TYPE_FORMAT, bytes)
        
        header = {
            'opcode': Utils.bytesToInt(opcode),
            'checksum': Utils.bytesToInt(checksum),
            'nseq': Utils.bytesToInt(nseq)
        }
        payload = {
            'chunksize': Utils.bytesToInt(chunksize),
        }

        return header, payload