import threading
from common.Logger import *

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
                case 0: # Upload
                    self.protocol.upload(self.firstPacketPayload['fileSize'], 
                                         self.firstPacketPayload['fileName'], 
                                         self.firstPacketPayload['md5'])
                    self.force_stop()
                case 2: # Download
                    #print('downloading (stop and wait): '+ str(message))
                    #StopAndWait.download()
                    continue
                case 7: # List
                    #StopAndWait.list(message)
                    continue
                case default:
                    Logger.LogError(f"The value {self.firstPacketHeader['opcode']} is not a valid opcode")
                    
            #modifiedMessage = message.decode().upper()

    def force_stop(self):
        self.allowedToRun = False
        self.protocol.closeSocket()