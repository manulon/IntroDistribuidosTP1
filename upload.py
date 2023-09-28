import hashlib
import sys
import getopt
import os
from client.Client import Client
from client.ClientSelectiveRepeat import ClientSelectiveRepeat
from common.constants import *
from client.ClientStopAndWait import *

def main(argv):
    verbosity = 0  # por defecto verbose 0
    host_service_ip_address = "localhost"  # por defecto localhost
    port_service_port = 16001  # por defecto 16001
    storage = ""
    file_name = None
    
    try:
        opts, args = getopt.getopt(argv, "hvqH:p:d:n:", ["help", "verbose", "quiet", "host=", "port=", "dst=", "name="])
    except getopt.GetoptError:
        sys.exit(2)

    for opt, arg in opts:
        # Selecciono la opcion h
        if opt in ("-h", "--help"): 
            print("Optional arguments")
            print("  -h, --help     list of commands")
            print("  -v, --verbose  increase output verbosity")
            print("  -q, --quiet    decrease output verbosity")
            print("  -H, --host     service IP address")
            print("  -p, --port     service port")
            print("  -d, --dst      destination file path")
            print("  -n, --name     file name")
            return
        # Selecciono la opcion v [NO SE PARA QUE SE USA]
        elif opt in ("-v", "--verbose"):
            print("ok verbose")
        # Selecciono la opcion q [NO SE PARA QUE SE USA]
        elif opt in ("-q", "--quiet"):
            verbosity = 0
            if verbosity == 0:
                print(f"{COLOR_BLUE}[INFO]{COLOR_END}"
                      " - q")
        # Selecciono la opcion H
        elif opt in ("-H", "--host"):
            host_service_ip_address = arg
            if verbosity != 0:
                print(f"{COLOR_BLUE}[INFO]{COLOR_END}"
                      f" - H={host_service_ip_address}")
        # Selecciono la opcion p
        elif opt in ("-p", "--port"):
            port_service_port = int(arg)
            if verbosity != 0:
                print(f"{COLOR_BLUE}[INFO]{COLOR_END}"
                    f" - p={port_service_port}")
        # Selecciono la opcion d [NO SE USA AUN]
        elif opt in ("-d", "--dst"):
            storage = arg
            if storage[-1] != '/':
                storage += '/'
            if not os.path.isdir(storage):
                print(f"{COLOR_RED}[ERROR]{COLOR_END}"
                    " - Invalid path")
                return
            if verbosity != 0:
                print(f"{COLOR_BLUE}[INFO]{COLOR_END}"
                    f" - s={storage}")
        # Selecciono la opcion n [NO SE USA AUN]
        elif opt in ("-n", "--name"):
            file_name = arg
            if verbosity != 0:
                print(f"{COLOR_BLUE}[INFO]{COLOR_END}"
                    f" - n={file_name}")

    if file_name == None:
        print(f"{COLOR_RED}[ERROR]{COLOR_END}"
            " - File name not specified")
        return

    client = Client(host_service_ip_address, port_service_port)

    has_protocol = False
    while (has_protocol == False):
        protocol = input('Ingrese el protocolo que queres utilizar: \n 1) Selective Repeat \n 2) Stop and Wait \n')
        if (protocol == '1'):
            client.setProtocol(ClientSelectiveRepeat())
            has_protocol = True
        elif (protocol == '2'):
            client.setProtocol(ClientStopAndWait())
            has_protocol = True
        else:
            print('La opcion seleccionada no es valida. \n')

    client.upload(file_name)

    client.close()

if __name__ == '__main__':
    main(sys.argv[1:])