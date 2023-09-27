class Utils:
    def bytes(self, n):
        bytes_ = bytes([0x0])
        for i in range(n-1):
            bytes_ += bytes([0x0])
        return bytes_

    def bytesToInt(self, bytes_):
        return int.from_bytes(bytes_, byteorder='little')