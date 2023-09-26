import struct

HEADER_FORMAT = "!B I I"
UPLOAD_REQUEST_FORMAT = "!20s Q 16s"
OPCODE_MASK = 0xF

class Packet:

    def pack_upload_request(self, checksum, nseq, filename, filesize, md5):
        return struct.pack(HEADER_FORMAT + UPLOAD_REQUEST_FORMAT, 0 & OPCODE_MASK, checksum, nseq, filename, filesize, md5)

    def unpack_upload_request(self, bytes):
        return struct.unpack(HEADER_FORMAT + UPLOAD_REQUEST_FORMAT, bytes)
    
    

    

    