import sys

'''Colores para prints'''
COLOR_GREEN = '\033[92m'
COLOR_BLUE = '\033[94m'
COLOR_RED = '\033[91m'
COLOR_YELLOW = '\033[93m'
COLOR_PURPLE = '\033[95m'
COLOR_BOLD = '\033[1m'
COLOR_END = '\033[0m'

'''Endianess'''
BYTEORDER = byteorder = sys.byteorder

'''Protocolo'''
CHUNKSIZE = 4096

'''Paquetes'''
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

FILE_TRANSFER_TYPE_FORMAT = '4s'

PACKAGE_FORMAT = '4096s'

STOP_FILE_TRANSFER_FORMAT = '16s1s'

'''Largo de paquetes (en bytes)'''
FILE_TRANSFER_REQUEST_SIZE = 62
FILE_TRANSFER_TYPE_RESPONSE_SIZE = 13
ACK_SIZE = 9
PACKET_SIZE = 4105
STOP_FILE_TRANSFER_SIZE = 26

'''Timeouts'''
SELECTIVE_REPEAT_PACKET_TIMEOUT = 3
CLIENT_SOCKET_TIMEOUTS = 5000
LAST_ACK_PACKET_TIMEOUT = 1000

'''Log Levels'''
LOG_LEVEL_ERROR = 0
LOG_LEVEL_WARNING = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_DEBUG = 3

'''Tipos de protocolo'''
STOP_AND_WAIT = 0
SELECTIVE_REPEAT = 1

