from common.constants import BYTEORDER
from shutil import disk_usage


class Utils:

    @staticmethod
    def bytes(n):
        bytes_ = bytes([0x0])
        for i in range(n - 1):
            bytes_ += bytes([0x0])
        return bytes_

    @staticmethod
    def bytesToInt(_bytes):
        return int.from_bytes(_bytes, byteorder='little')

    @staticmethod
    def bytesNumerados(n, digit):
        bytes_ = digit.to_bytes(1, BYTEORDER)
        for i in range(n - 1):
            bytes_ += digit.to_bytes(1, BYTEORDER)
        return bytes_

    @staticmethod
    def getFreeDiskSpace():
        _, _, free = disk_usage("/")
        return free
