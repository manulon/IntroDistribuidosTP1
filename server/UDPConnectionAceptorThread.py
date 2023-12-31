import threading
from common.Logger import Logger
from common.Utils import Utils
from common.Checksum import Checksum
from common.Packet import Packet
from common.constants import COLOR_BLUE, COLOR_END, \
    FILE_TRANSFER_REQUEST_SIZE, BYTEORDER
from common.Socket import Socket
from server.ServerStopAndWait import ServerStopAndWait
from server.UDPServerThread import UDPServerThread
from server.ServerSelectiveRepeat import ServerSelectiveRepeat


class UDPConnectionAceptorThread(threading.Thread):

    def __init__(self, serverSocket, clients, storage):
        threading.Thread.__init__(self)
        self.serverSocket = serverSocket
        self.clients = clients
        self.allowedToRun = True
        self.lastSocketPort = serverSocket.getPort()
        self.serverAddress = serverSocket.getAddress()
        self.storage = storage

    def run(self):
        while self.allowedToRun:
            firstPacketIsValid = False
            if not firstPacketIsValid:
                try:
                    self.serverSocket.settimeout(0.2)
                    firstPacketIsValid, header, payload, \
                        clientAddress, clientPort = \
                        self.receiveFirstPacket()
                    if firstPacketIsValid:
                        if (clientAddress, clientPort) not in self.clients:
                            print(
                                f"{COLOR_BLUE}[INFO]"
                                f"{COLOR_END}"
                                f" - New UDP Client {clientAddress}"
                                f":{clientPort} connected.")

                        self.lastSocketPort += 1
                        newSocket = Socket(
                            self.lastSocketPort, self.serverAddress)

                        match payload['protocol']:
                            case 2:  # STOP & WAIT
                                protocol = ServerStopAndWait(newSocket,
                                                             clientAddress,
                                                             clientPort,
                                                             self.storage)
                                Logger.LogInfo('Selected stop and wait')

                            case 1:  # SELECTIVE REPEAT
                                protocol = ServerSelectiveRepeat(newSocket,
                                                                 clientAddress,
                                                                 clientPort,
                                                                 self.storage)
                                Logger.LogInfo('Selected Selective Repeat')

                        self.clients[(clientAddress,
                                      clientPort)] = \
                            UDPServerThread(protocol,
                                            header,
                                            payload)
                        self.clients[(clientAddress, clientPort)].start()
                except BaseException:
                    continue

    def receiveFirstPacket(self):
        received_message, (clientAddress, clientPort) \
            = self.serverSocket.receive(
                FILE_TRANSFER_REQUEST_SIZE)

        header = None
        payload = None

        Logger.LogDebug(
            f"I receive a packet with opcode \
                {Utils.bytesToInt(received_message[:1])}")

        if Utils.bytesToInt(received_message[:1]) == 0:
            header, payload = Packet.unpack_upload_request(received_message)
        elif Utils.bytesToInt(received_message[:1]) == 2:
            header, payload = Packet.unpack_download_request(received_message)

        firstPacketIsValid = self.isChecksumOK(header, payload)

        return firstPacketIsValid, header, payload, clientAddress, clientPort

    def isChecksumOK(self, header, payload):
        Logger.LogDebug(f"{header}")
        opcode = header['opcode'].to_bytes(1, BYTEORDER)
        checksum = (header['checksum']).to_bytes(4, BYTEORDER)
        nseqToBytes = header['nseq'].to_bytes(1, BYTEORDER)

        return Checksum.is_checksum_valid(checksum +
                                          opcode +
                                          nseqToBytes,
                                          len(opcode +
                                              checksum +
                                              nseqToBytes))

    def force_stop(self):
        self.allowedToRun = False
        self.serverSocket.close()
        for k in self.clients.keys():
            self.clients[k].join()
            Logger.LogDebug(f"The connection with {k[0]}:{k[1]} is finished.")
