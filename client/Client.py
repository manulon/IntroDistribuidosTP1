from common.Socket import Socket


class Client:
    def __init__(self, address, port, storage):
        self.port = port
        self.serverPort = 16000
        self.address = address
        self.serverAddress = 'localhost'
        self.socket = Socket(self.port, self.address)
        self.protocol = None
        self.storage = storage

    def upload(self, filename):
        self.protocol.upload(filename)

    def download(self, filename):
        self.protocol.download(filename)

    def setProtocol(self, protocol):
        protocol.setServerInfo(
            self.serverAddress,
            self.serverPort,
            self.socket)
        # TODO: Agregar función setStorage() en ClienStopAndWait
        protocol.setStorage(self.storage)
        self.protocol = protocol

    def close(self):
        self.socket.close()
