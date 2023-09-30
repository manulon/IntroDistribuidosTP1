import threading

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
                    self.protocol.upload(self.firstPacketPayload['fileSize'])
                    self.force_stop()
                case 2: # Download
                    #print('downloading (stop and wait): '+ str(message))
                    #StopAndWait.download()
                    break
                case 7: # List
                    #StopAndWait.list(message)
                    break
                case default:
                    # print("message not understood")
                    # close connection
                    break
            #modifiedMessage = message.decode().upper()
        print('Sali del while de udp server thread')

    def force_stop(self):
        self.allowedToRun = False
        self.protocol.closeSocket()