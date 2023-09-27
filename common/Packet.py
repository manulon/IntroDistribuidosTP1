import struct
from common.Utils import Utils

REQUEST_CONTENT = "20s"
OPCODE_MASK = 0xF

OPCODE_FORMAT = 'c'
CHECKSUM_FORMAT = '4s'
NSEQ_FORMAT = '4s'
HEADER_FORMAT = OPCODE_FORMAT + CHECKSUM_FORMAT + NSEQ_FORMAT

PROTOCOL_FORMAT = 'c'
FILE_NAME_FORMAT = '20s'
FILE_SIZE_FORMAT = '16s'
MD5 = '16s'
UPLOAD_REQUEST_FORMAT = PROTOCOL_FORMAT + FILE_NAME_FORMAT + FILE_SIZE_FORMAT + MD5
class Packet:
    def pack_upload_request(self, header, payload):
        opcode = header[0]
        checksum = header[1]
        nseq = header[2]
        protocol = payload[0]
        fileName = payload[1]
        fileSize = payload[2]
        md5 = payload[3]
        return struct.pack(HEADER_FORMAT + UPLOAD_REQUEST_FORMAT, opcode, checksum, nseq, protocol, fileName, fileSize, md5)

    def unpack_upload_request(self, bytes):
        utils = Utils()
        opcode, checksum, nseq, protocol, fileName, fileSize, md5 = struct.unpack(HEADER_FORMAT + UPLOAD_REQUEST_FORMAT, bytes)
        header = {
            'opcode': utils.bytesToInt(opcode),
            'checksum': utils.bytesToInt(checksum),
            'nseq': utils.bytesToInt(nseq)
        }
        payload = {
            'protocol': utils.bytesToInt(protocol),
            'fileName': fileName.decode(),
            'fileSize': utils.bytesToInt(fileSize),
            'md5': md5.decode()
        }
        return header, payload