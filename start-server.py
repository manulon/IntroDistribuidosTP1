import sys
from server.Server import Server

def main(argv):
    server = Server()
    server.receive()

if __name__ == '__main__':
    main(sys.argv[1:])
