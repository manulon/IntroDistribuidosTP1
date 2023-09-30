import sys
import getopt
import os
from client.Client import Client
from client.ClientSelectiveRepeat import ClientSelectiveRepeat
from common.constants import *
from client.ClientStopAndWait import *
from common.Logger import Logger

def main(argv):
    Logger.SetLogLevel(LOG_LEVEL_WARNING)
    host_service_ip_address = "localhost"  # por defecto localhost
    port_service_port = 16001  # por defecto 16001
    storage = ""
    file_name = None
    
    try:
        opts, args = getopt.getopt(argv, "hvqH:p:d:n:", ["help", "verbose", "quiet", "host=", "port=", "dst=", "name="])
    except getopt.GetoptError:
        sys.exit(2)

    for opt, arg in opts:
        # HELP
        if opt in ("-h", "--help"): 
            print("usage: upload [-h] [-v | -q] [-H ADDR] [-p PORT] [-s FILEPATH] [-n FILENAME]")
            print()
            print("Upload a file up to 4 gb to a server, using UDP over an RDT connection")
            print("It supports:")
            print("\tSelective Repeat")
            print("\tStop and wait")
            print()
            print("optional arguments:")
            print("  -h, --help     show this help message and exit")
            print("  -v, --verbose  increase output verbosity")
            print("  -q, --quiet    decrease output verbosity")
            print("  -H, --host     server IP address")
            print("  -p, --port     server port")
            print("  -s, --src      source file path")
            print("  -n, --name     file name")
            return
        
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
            port_service_port = int(arg)
            Logger.LogInfo(f"Port set to {port_service_port}")
            
        # SOURCE
        elif opt in ("-s", "--src"):
            storage = arg
            if storage[-1] != '/':
                storage += '/'
            if not os.path.isdir(storage):
                Logger.LogError(f"Invalid path {storage}")
                return
            Logger.LogInfo(f"Source {storage}")

        # NAME
        elif opt in ("-n", "--name"):
            file_name = arg
            if file_name:
                Logger.LogInfo(f"File name {file_name}")

    if file_name == None or file_name == "" or not file_name:
        Logger.LogError("No file specified")
        return

    client = Client(host_service_ip_address, port_service_port)

    has_protocol = False
    while (has_protocol == False):
        protocol = input('What protocol do you want to use?: \n 1) Selective Repeat \n 2) Stop and Wait \n')
        if (protocol == '1'):
            client.setProtocol(ClientSelectiveRepeat())
            has_protocol = True
        elif (protocol == '2'):
            client.setProtocol(ClientStopAndWait())
            has_protocol = True
        else:
            Logger.LogWarning(f"The value {protocol} is not valid")
            print('Invalid option. \n')

    client.upload(file_name)

    client.close()

if __name__ == '__main__':
    main(sys.argv[1:])