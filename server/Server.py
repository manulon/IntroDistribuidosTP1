from socket import *
from common.Socket import Socket
from common.Packet import Packet
from common.constants import *
from common.Logger import *
from common.Checksum import *
from server.ServerSelectiveRepeat import *
from server.UDPConnectionAceptorThread import *


class Server():
    def __init__(self, address, port, storage):
        self.port = port
        self.address = address
        self.socket = Socket(self.port, self.address)
        self.protocol = None
        self.clients = {}
        self.connectionAceptorThread = None
        self.storage = storage

    def start(self):
        #if self.verbosity >= 1:
        self.startServer()
        
        print("\033[1mTo close the server type 'q':\033[0m")
        while True:
            user_input = input()
            if user_input == 'q':
                print(f"{COLOR_BLUE}[INFO]{COLOR_END}"
                     " - Closing the Server...")
                
                self.connectionAceptorThread.force_stop()
                self.connectionAceptorThread.join()
                
                print(f"{COLOR_BLUE}[INFO]{COLOR_END}"
                    " - The Server has been succesfully closed.")
                break
            else:
                print("\033[1mThe key entered is invalid. To close the server type 'q':\033[0m")

    def startServer(self):
        print(f"{COLOR_BLUE}[INFO]{COLOR_END}"f" - Starting the Server...")

        self.connectionAceptorThread = UDPConnectionAceptorThread(self.socket, self.clients)
        self.connectionAceptorThread.start()

        print(f"{COLOR_BLUE}[INFO]{COLOR_END}"" - UDP Server started.")

    def close(self):
        self.socket.close()
