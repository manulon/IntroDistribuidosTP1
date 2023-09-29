from common.Packet import Packet
import os
from common.Hasher import Hasher
from Server import Server
from common.Utils import Utils

class StopAndWait:
    def __init__(self, client):
        self.client = client

    def upload(self, filename, file_size, received_md5):
        """ 
            Mandar el OK o ERROR (filesize o repetido) por upload
            Recibir data (partes del archivo) y guardarla
            Devolver ACK por cada paquete recibido
            FIN
        """
        # checksum = Hasher.checksum(package)
        utils = Utils()
        checksum = 0
        filename = "archivo.txt"    
        file_size = os.stat(filename).st_size
        with open(filename, 'rb') as f:
            read_bytes = f.read()
            md5 = Hasher.md5(read_bytes)
            if md5 == received_md5:
                print("El archivo es igual")
                if utils.bytesToInt(file_size) > Server.MAX_FILE_SIZE:
                    message = Packet.pack_file_too_big_error()
                    print('El archivo es muy grande')
                # if filename in filelist:
                    # message = Packet.pack_file_already_exists_error()
                
                message = Packet.pack_file_transfer_response()
                self.client.send(message)
            else:
                # no hacemos nada o error?
                print('El archivo no es igual')
            

    def download(self, filename):
        pass

