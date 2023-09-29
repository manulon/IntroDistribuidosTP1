import getopt
import sys
from server.Server import Server

def main(argv):
    verbosity = 0
    host_service_ip_address = 'localhost'
    port_service_port = 16000
    storage = ""

    try:
        opts, args = getopt.getopt(argv, "hvqH:p:s:", ["help", "verbose", "quiet", "host=", "port=", "storage="])
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
            print("  -s, --storage  storage dir path")
        # Selecciono la opcion v [NO SE PARA QUE SE USA]
        elif opt in ("-v", "--verbose"):
            print("ok verbose")
            vervosity += 1
        # Selecciono la opcion q [NO SE PARA QUE SE USA]
        elif opt in ("-q", "--quiet"):
            print("ok quiet")
            vervosity -= 1
        # Selecciono la opcion h
        elif opt in ("-H", "--host"):
            host_service_ip_address = arg
            print("ok IP address ", host_service_ip_address)
        # Selecciono la opcion p
        elif opt in ("-p", "--port"):
            port_service_port = arg
            print("ok port ", port_service_port)
        # Selecciono la opcion s [NO SE USA AUN]
        elif opt in ("-s", "--storage"):
            storage = arg
            print("ok storage path ", storage)


    server = Server(host_service_ip_address, port_service_port)
    server.start()
    #server.close()

if __name__ == '__main__':
    main(sys.argv[1:])
