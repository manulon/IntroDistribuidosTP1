from common.Packet import Packet
import os
from common.Hasher import Hasher

class StopAndWait:
    def __init__(self, client):
        self.client = client

    def upload(self, file):
        """ 
            Mandar el OK o ERROR (filesize o repetido) por upload
            Recibir data (partes del archivo) y guardarla
            Devolver ACK por cada paquete recibido
            FIN
        """
        # checksum = Hasher.checksum(package)
        checksum = 0
        filename = "archivo.txt"    
        file_size = os.stat(filename).st_size
        with open(filename, 'rb') as f:
            read_bytes = f.read()
            md5_encoding = Hasher.md5(read_bytes)
            message = Packet.pack_upload_request(checksum, 0, filename, file_size, md5_encoding)
            self.client.send(message)

    def download(self, filename):
        pass

