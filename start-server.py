import os
import getopt
import sys
from common.constants import *
from server.Server import Server
from common.Logger import Logger

def main(argv):
    Logger.SetLogLevel(LOG_LEVEL_WARNING)
    host_service_ip_address = 'localhost'
    port_service_port = 16000
    storage = "./server_files/"

    try:
        opts, args = getopt.getopt(argv, "hvqH:p:s:", ["help", "verbose", "quiet", "host=", "port=", "storage="])
    except getopt.GetoptError:
        sys.exit(2)
    for opt, arg in opts:
        # HELP
        if opt in ("-h", "--help"):
            print("usage: start-server [-h] [-v | -q] [-H ADDR] [-p PORT] [-s DIRPATH]")
            print()
            print("Upload/Download a file up to 4 gb from the server, using UDP over an RDT connection")
            print("It supports:")
            print("\tSelective Repeat")
            print("\tStop and wait")
            print()
            print("Optional arguments")
            print("  -h, --help     shows this help message and exit")
            print("  -v, --verbose  increase output verbosity")
            print("  -q, --quiet    decrease output verbosity")
            print("  -H, --host     service IP address")
            print("  -p, --port     service port")
            print("  -s, --storage  storage dir path")
        
        # VERBOSE
        elif opt in ("-v", "--verbose"):
            Logger.SetLogLevel(LOG_LEVEL_DEBUG)
            Logger.LogInfo("Verbosity will now be set to Debug")            

        # QUIET
        elif opt in ("-q", "--quiet"):
            Logger.LogInfo("Verbosity will now be set to Error")
            Logger.SetLogLevel(LOG_LEVEL_ERROR)            

        # HOST
        elif opt in ("-H", "--host"):
            host_service_ip_address = arg
            Logger.LogInfo(f"Host set to {host_service_ip_address}")

        # PORT
        elif opt in ("-p", "--port"):
            port_service_port = arg
            Logger.LogInfo(f"Port set to {port_service_port}")

        # STORAGE
        elif opt in ("-s", "--storage"):
            storage = arg
            if storage[-1] != '/':
                storage += '/'
            Logger.LogInfo(f"Storage {storage}")


    server = Server(host_service_ip_address, port_service_port, storage)
    server.receive()

if __name__ == '__main__':
    main(sys.argv[1:])
