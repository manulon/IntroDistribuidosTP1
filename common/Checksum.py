import sys
from common.Logger import Logger
BYTEORDER = byteorder = sys.byteorder


class Checksum:

    @staticmethod
    def get_checksum(content, size, message=''):
        cksum = 0
        pointer = 0
        # The main loop adds up each set of 4 bytes.
        # They are first converted to strings,
        # concatenated converted to integers,
        # and then added to the sum.
        while size >= 4:
            cksum += int((str("%02x" % (content[pointer],))
                         + str("%02x" % (content[pointer + 1],))
                         + str("%02x" % (content[pointer + 2],))
                         + str("%02x" % (content[pointer + 3],))), 16)
            size -= 4
            pointer += 4

        if size == 3:
            cksum += content[pointer] + \
                content[pointer + 1] + content[pointer + 2]

        if size == 2:
            cksum += content[pointer] + content[pointer + 1]

        if size == 1:
            cksum += content[pointer]

        cksum = (cksum >> 32) + (cksum & 0xffffffff)
        cksum += (cksum >> 32)

        result = (~cksum) & 0xFFFFFFFF
        resultAsBytes = result.to_bytes(4, BYTEORDER)

        Logger.LogDebug(f"Checksum: {result} \t{message}")

        if BYTEORDER == 'little':  # reverse them if little endian
            resultAsBytes = resultAsBytes[::-1]

        return resultAsBytes

    @staticmethod
    def is_checksum_valid(content, size):
        return Checksum.get_checksum(
            content, size, '(validation)') == (0).to_bytes(
            4, BYTEORDER)
