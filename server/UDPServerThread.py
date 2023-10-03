import threading
from common.Logger import Logger


class UDPServerThread(threading.Thread):

    def __init__(self, protocol, firstPacketHeader, firstPacketPayload):
        threading.Thread.__init__(self)
        self.protocol = protocol
        self.firstPacketHeader = firstPacketHeader
        self.firstPacketPayload = firstPacketPayload
        self.allowedToRun = True

    def run(self):
        while self.allowedToRun:
            match self.firstPacketHeader['opcode']:
                case 0:  # Upload
                    Logger.LogDebug("Im going to start an upload")
                    self.protocol.upload(self.firstPacketPayload['fileSize'],
                                         self.firstPacketPayload['fileName'],
                                         self.firstPacketPayload['md5'])
                    self.force_stop()
                case 2:  # Download
                    Logger.LogDebug("Im going to start a download")
                    self.protocol.download(self.firstPacketPayload['fileName'])
                    self.force_stop()
                    continue
                case 7:  # List
                    # StopAndWait.list(message)
                    continue
            # modifiedMessage = message.decode().upper()

    def force_stop(self):
        self.allowedToRun = False
        self.protocol.closeSocket()
