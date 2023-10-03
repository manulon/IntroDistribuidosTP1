import hashlib
import math
import os
import time
from common.Logger import Logger
from common.Checksum import Checksum
from common.Packet import Packet
import common.constants as const
from common.Utils import Utils


class ServerStopAndWait:
    def __init__(self, socket, clientAddress, clientPort, storage):
        self.socket = socket
        self.clientAddress = clientAddress
        self.clientPort = clientPort
        self.protocolID = bytes([const.STOP_AND_WAIT])
        self.storage = storage

    def send(self, message):
        self.socket.send(message, self.clientAddress, self.clientPort)

    def sendFileTransferTypeResponse(self, fileSize):
        socketTimeouts = 0
        errorReceived = False
        if fileSize > const.MAX_FILE_SIZE:
            self.sendFileTooBigError()
            errorPacketSentTime = time.time()
            while socketTimeouts < const.LAST_ACK_PACKET_TIMEOUT and (
                not errorReceived
            ):
                try:
                    self.socket.settimeout(const.TIMEOUT)
                    ackNseq = self.receiveACK()
                    socketTimeouts = 0
                    errorReceived = True
                except TimeoutError:
                    # We assume the client has already sent
                    # the ACK and closed the connection
                    Logger.LogWarning("There has been an ACK \
                                      timeout for an error")
                    socketTimeouts += 1
                if (not errorReceived) and (
                    time.time() - errorPacketSentTime
                    > const.SELECTIVE_REPEAT_PACKET_TIMEOUT
                ):
                    self.sendFileTooBigError()
                    errorPacketSentTime = time.time()
            return const.FILE_TOO_BIG_OPCODE

        if fileSize > Utils.getFreeDiskSpace():
            self.sendNoDiskSpaceError()
            errorPacketSentTime = time.time()
            while socketTimeouts < const.LAST_ACK_PACKET_TIMEOUT and (
                not errorReceived
            ):
                try:
                    self.socket.settimeout(const.TIMEOUT)
                    ackNseq = self.receiveACK()
                    socketTimeouts = 0
                    errorReceived = True
                except TimeoutError:
                    # We assume the client has already sent
                    # the ACK and closed the connection
                    Logger.LogWarning("There has been an ACK \
                                      timeout for an error")
                    socketTimeouts += 1
                if (not errorReceived) and (
                    time.time() - errorPacketSentTime
                    > const.SELECTIVE_REPEAT_PACKET_TIMEOUT
                ):
                    self.sendNoDiskSpaceError()
                    errorPacketSentTime = time.time()
            return const.NO_DISK_SPACE_OPCODE

        opcode = bytes([const.FILE_TRANSFER_RESPONSE_OPCODE])
        zeroedChecksum = (0).to_bytes(4, const.BYTEORDER)
        nseq = (0).to_bytes(4, const.BYTEORDER)
        finalChecksum = Checksum.get_checksum(
            zeroedChecksum + opcode + nseq,
            len(opcode + zeroedChecksum + nseq), 'sendACK')
        header = (opcode, finalChecksum, nseq)

        # fixed chunksize (4096 bytes)
        chunksize = const.CHUNKSIZE.to_bytes(4, const.BYTEORDER)

        message = Packet.pack_file_transfer_type_response(header, chunksize)
        self.send(message)
        return const.FILE_TRANSFER_RESPONSE_OPCODE

    def sendFileTooBigError(self):
        opcode = bytes([const.FILE_TOO_BIG_OPCODE])
        zeroedChecksum = (0).to_bytes(4, const.BYTEORDER)
        nseq = (0).to_bytes(4, const.BYTEORDER)
        finalChecksum = Checksum.get_checksum(
            zeroedChecksum + opcode + nseq,
            len(opcode + zeroedChecksum + nseq), 'sendACK')
        header = (opcode, finalChecksum, nseq)

        message = Packet.pack_file_too_big_error(header)
        self.send(message)

    def sendNoDiskSpaceError(self):
        opcode = bytes([const.NO_DISK_SPACE_OPCODE])
        zeroedChecksum = (0).to_bytes(4, const.BYTEORDER)
        nseq = (0).to_bytes(4, const.BYTEORDER)
        finalChecksum = Checksum.get_checksum(
            zeroedChecksum + opcode + nseq,
            len(opcode + zeroedChecksum + nseq), 'sendACK')
        header = (opcode, finalChecksum, nseq)

        message = Packet.pack_no_disk_space_error(header)
        self.send(message)

    def upload(self, fileSize, fileName, originalMd5):
        fileName = fileName.rstrip('\x00')
        opcode = self.sendFileTransferTypeResponse(fileSize)
        if opcode == const.FILE_TOO_BIG_OPCODE:
            Logger.LogError("File too big")
            return
        elif opcode == const.NO_DISK_SPACE_OPCODE:
            Logger.LogError("No disk space")
            return

        totalPackets = fileSize / const.CHUNKSIZE
        acksSent = 0
        nextNseq = 1
        file = []

        while acksSent < totalPackets:
            header, payload = self.receivePacket()
            if header['nseq'] == nextNseq:
                if self.isChecksumOK(header, payload):
                    self.sendACK(header['nseq'])
                    file.append(payload)
                    nextNseq = acksSent % 2
                    acksSent += 1
            else:  # client resends packet - cases 3 (lost ACK) and 4 (timeout)
                # server only resends ACK (detects duplicate)
                self.sendACK(header['nseq'])
                Logger.LogDebug(f"Sending ACK {header['nseq']}")

        bytesInLatestPacket = fileSize % const.CHUNKSIZE
        Logger.LogWarning(
            f"There are {bytesInLatestPacket} \
            bytes on the last packet. removing padding")
        file[len(file) - 1] = file[len(file) - 1][0:bytesInLatestPacket]
        Logger.LogWarning("Padding removed")

        # if state == STATE_OK:
        self.saveFile(file, fileName)
        md5, state = self.checkFileMD5(fileName, originalMd5)
        self.stopFileTransfer(nextNseq, fileName, md5, state)

    def download(self, filename):
        filename = filename.rstrip('\x00')
        file: bytes
        completeName = os.path.join(self.storage, filename)
        Logger.LogInfo(f"Download request for file: {completeName}")
        try:
            with open(completeName, 'rb') as file:
                file = file.read()
        except FileNotFoundError:
            Logger.LogError(f"File {filename} not found")
            socketTimeouts = 0
            errorReceived = False
            self.sendFileDoesNotExistError()
            errorPacketSentTime = time.time()
            while socketTimeouts < const.LAST_ACK_PACKET_TIMEOUT and (
                not errorReceived
            ):
                try:
                    self.socket.settimeout(const.TIMEOUT)
                    ackNseq = self.receiveACK()
                    Logger.LogDebug(f"Received ACK with nseq: {ackNseq}")
                    socketTimeouts = 0
                    errorReceived = True
                except TimeoutError:
                    socketTimeouts += 1
                if (not errorReceived) and (
                    time.time() - errorPacketSentTime
                    > const.SELECTIVE_REPEAT_PACKET_TIMEOUT
                ):
                    Logger.LogWarning(
                        f"There has been a timeout in Sending \
                        file does not exist error packet. Retransmiting packet")
                    self.sendFileDoesNotExistError()
                    errorPacketSentTime = time.time()
            return

        md5 = hashlib.md5(file)
        filesize = len(file)
        receivedErrorCode = self.sendDownloadRequestResponse(file, md5)
        if receivedErrorCode:
            Logger.LogError("The transaction could not be completed because \
                            the client has not enough space in his disk")
            self.sendACK(0)
            return
        totalPackets = math.ceil(filesize / const.CHUNKSIZE)
        Logger.LogInfo(
            f"File: {filename} - Size: {filesize} - md5: \
            {md5.hexdigest()} - Packets to send: {totalPackets}")
        self.sendFile(file, const.CHUNKSIZE)
        Logger.LogInfo('File transfer has ended.')

    def sendFile(self, file, chunksize):
        fileSize = len(file)
        totalPackets = fileSize / chunksize
        packetsPushed = 0

        socketTimeouts = 0
        ackNseq = -1
        while (packetsPushed < totalPackets and socketTimeouts <
               const.CLIENT_SOCKET_TIMEOUTS):
            sequenceNumber = (packetsPushed + 1) % 2  # starts in 1
            payload = file[packetsPushed *
                           chunksize: (packetsPushed + 1) * chunksize]
            self.sendPacket(sequenceNumber, payload)
            Logger.LogDebug(f"Sending packet with nseq: {sequenceNumber}")
            packetSentTime = time.time()
            try:
                self.socket.settimeout(const.TIMEOUT)
                ackNseq = self.receiveACK()
                Logger.LogDebug(f"Received ACK with nseq: {ackNseq}")
                socketTimeouts = 0
                packetsPushed += 1
                while (ackNseq != sequenceNumber and socketTimeouts <
                       const.CLIENT_SOCKET_TIMEOUTS):  # case 4
                    self.sendPacket(sequenceNumber, payload)
                    try:
                        self.socket.settimeout(const.TIMEOUT)
                        ackNseq = self.receiveACK()
                        Logger.LogDebug(f"Received ACK with nseq: {ackNseq}")
                        socketTimeouts = 0
                    except TimeoutError:
                        socketTimeouts += 1
                    except BaseException:
                        Logger.LogError(
                            "There has been an error receiving the ACK")
            except TimeoutError:
                socketTimeouts += 1
            except BaseException:
                Logger.LogError("There has been an error receiving the ACK")
            if (ackNseq != sequenceNumber) and (
                    time.time() - packetSentTime
                    > const.SELECTIVE_REPEAT_PACKET_TIMEOUT
                ):
                    Logger.LogWarning(
                        f"There has been a timeout in Sending \
                        the packet with nseq {sequenceNumber}. Retransmiting packet")
                    self.sendPacket(sequenceNumber, payload)
                    packetSentTime = time.time()

            # Case 1: Packet received => ACK received
            # Case 2: Packet lost => timeout => do nothing (resend)
            # Case 3: Packet received, ACK lost => timeout
            # => do nothing (resend)
            # Case 4: ACK not received before timeout => timeout => resend
            # packet => receive ack1 twice (resend next packet)

    def sendPacket(self, nseq, payload):
        opcode = bytes([const.PACKET_OPCODE])
        zeroedChecksum = (0).to_bytes(4, const.BYTEORDER)
        nseqToBytes = (nseq).to_bytes(4, const.BYTEORDER)
        finalChecksum = Checksum.get_checksum(
            zeroedChecksum + opcode + nseqToBytes, len(
                opcode + zeroedChecksum + nseqToBytes), 'sendPackage')
        header = (opcode, finalChecksum, nseqToBytes)

        message = Packet.pack_package(header, payload)
        self.send(message)

    def sendDownloadRequestResponse(self, file, md5):
        opcode = bytes([const.DOWNLOAD_REQUEST_RESPONSE_OPCODE])
        zeroedChecksum = (0).to_bytes(4, const.BYTEORDER)
        nseq = (0).to_bytes(4, const.BYTEORDER)
        finalChecksum = Checksum.get_checksum(zeroedChecksum +
                                              opcode +
                                              nseq,
                                              len(opcode +
                                                  zeroedChecksum +
                                                  nseq),
                                              'sendDownloadRequestResponse')
        fileSize = len(file).to_bytes(16, const.BYTEORDER)

        header = (opcode, finalChecksum, nseq)
        payload = (md5.digest(), fileSize)
        message = Packet.pack_download_response(header, payload)

        nextPacketIsAnOk = False
        ackReceived = False
        socketTimeouts = 0
        receivedErrorCode = False
        while (not ackReceived and socketTimeouts <
               const.LAST_ACK_PACKET_TIMEOUT and
               not (nextPacketIsAnOk or receivedErrorCode)):  # case 4
            self.send(message)
            try:
                self.socket.settimeout(const.TIMEOUT)
                receivedOpcode = self.receiveResponseACK()
                socketTimeouts = 0
                if receivedOpcode == const.NO_DISK_SPACE_OPCODE:
                    receivedErrorCode = True
                # If Client re-sent request (not nextPacketIsAnOk), send
                # message again
                if receivedOpcode != const.DOWNLOAD_REQUEST_OPCODE:
                    nextPacketIsAnOk = True
            except TimeoutError:
                socketTimeouts += 1
            except BaseException:
                Logger.LogError("There has been an \
                                error receiving the ACK")

        return receivedErrorCode

    def receivePacket(self):
        received_message, (serverAddres, serverPort) = self.socket.receive(
            const.PACKET_SIZE)
        if Utils.bytesToInt(received_message[:1]) == 0:
            header, payload = Packet.unpack_upload_request(received_message)
        else:
            header, payload = Packet.unpack_package(received_message)
        return header, payload

    def receiveResponseACK(self):
        received_message, (serverAddres, serverPort) = self.socket.receive(
            const.ACK_SIZE)

        header = Packet.unpack_ack(received_message)
        opcode = header['opcode'].to_bytes(1, const.BYTEORDER)
        checksum = (header['checksum']).to_bytes(4, const.BYTEORDER)
        nseqToBytes = header['nseq'].to_bytes(4, const.BYTEORDER)

        if Checksum.is_checksum_valid(checksum +
                                      opcode +
                                      nseqToBytes,
                                      len(opcode +
                                          checksum +
                                          nseqToBytes)):
            return header['opcode']
        else:
            Logger.LogWarning("Invalid checksum for ACK received")
            return (header['opcode'] + 1)

    def sendACK(self, nseq):
        opcode = bytes([const.ACK_OPCODE])
        checksum = (2).to_bytes(4, const.BYTEORDER)
        nseqToBytes = nseq.to_bytes(4, const.BYTEORDER)
        header = (opcode, checksum, nseqToBytes)

        message = Packet.pack_ack(header)
        self.send(message)

    def receiveACK(self):
        received_message, (serverAddres, serverPort) = self.socket.receive(
            const.ACK_SIZE)

        header = Packet.unpack_ack(received_message)
        opcode = header['opcode'].to_bytes(1, const.BYTEORDER)
        checksum = (header['checksum']).to_bytes(4, const.BYTEORDER)
        nseqToBytes = header['nseq'].to_bytes(4, const.BYTEORDER)

        if header['opcode'] == const.FILE_TOO_BIG_OPCODE:
            Logger.LogError("File too big")
            return const.ERROR_CODE

        if Checksum.is_checksum_valid(checksum +
                                      opcode +
                                      nseqToBytes,
                                      len(opcode +
                                          checksum +
                                          nseqToBytes)):
            return header['nseq']
        else:
            Logger.LogWarning("Invalid checksum for ACK receeived")
            return header['nseq']

    def saveFile(self, file, fileName):
        completeName = os.path.join(self.storage, fileName)
        os.makedirs(os.path.dirname(completeName), exist_ok=True)

        fileWriter = open(completeName, "wb")
        for i in range(0, len(file)):
            fileWriter.write(file[i])

        Logger.LogInfo(f"File written into: {completeName}")
        fileWriter.close()

    def isChecksumOK(self, header, payload):
        opcode = header['opcode'].to_bytes(1, const.BYTEORDER)
        checksum = (header['checksum']).to_bytes(4, const.BYTEORDER)
        nseqToBytes = header['nseq'].to_bytes(4, const.BYTEORDER)

        return Checksum.is_checksum_valid(
            checksum + opcode + nseqToBytes,
            len(opcode + checksum + nseqToBytes))

    def stopFileTransfer(self, nseq, fileName, md5, state):
        opcode = bytes([const.STOP_FILE_TRANSFER_OPCODE])
        zeroedChecksum = (0).to_bytes(4, const.BYTEORDER)
        nseqToBytes = nseq.to_bytes(4, const.BYTEORDER)
        finalChecksum = Checksum.get_checksum(
            zeroedChecksum + opcode + nseqToBytes, len(
                opcode + zeroedChecksum + nseqToBytes), 'sendACK')
        header = (opcode, finalChecksum, nseqToBytes)
        payload = (md5.digest(), state)
        message = Packet.pack_stop_file_transfer(header, payload)

        self.send(message)
        stopFileTransferMsgSentAt = time.time()

        communicationFinished = False
        stopCommunicationSocketTimeout = 0

        while (not communicationFinished) and (
                stopCommunicationSocketTimeout <
                const.LAST_ACK_PACKET_TIMEOUT
                ):
            try:
                self.socket.settimeout(const.TIMEOUT)
                received_message, (serverAddres, serverPort) =\
                    self.socket.receive(const.ACK_SIZE)
                stopCommunicationSocketTimeout = 0
                communicationFinished = True
            except TimeoutError:
                # We assume the client has already sent the ACK and closed the
                # connection
                stopCommunicationSocketTimeout += 1

            if (not communicationFinished) and (time.time() -
                                                stopFileTransferMsgSentAt >
                                                const.
                                                SELECTIVE_REPEAT_PACKET_TIMEOUT
                                                ):
                Logger.LogWarning(
                    f"There has been a timeout in Sending \
                    stop file transfer packet. Retransmiting packet")
                self.send(message)
                stopFileTransferMsgSentAt = time.time()

    def stopDownloading(self):
        communicationFinished = False
        stopCommunicationSocketTimeout = 0

        while (not communicationFinished) and (
                stopCommunicationSocketTimeout <
                const.LAST_ACK_PACKET_TIMEOUT):
            try:
                self.socket.settimeout(const.TIMEOUT)
                received_message, (serverAddres, serverPort) \
                    = self.socket.receive(
                    const.STOP_FILE_TRANSFER_SIZE)
                stopCommunicationSocketTimeout = 0
                communicationFinished = True
            except TimeoutError:
                # We assume the client closed the connection
                stopCommunicationSocketTimeout += 1

        header, payload = Packet.unpack_stop_file_transfer(received_message)
        Logger.LogInfo(f"Received ACK: {header['nseq']}")
        if payload["state"] == 0:
            Logger.LogError(
                "The client has reported an error downloading \
                the file. File received is corrupted.")

    def sendFileDoesNotExistError(self):
        opcode = bytes([const.FILE_DOES_NOT_EXIST_OPCODE])
        zeroedChecksum = (0).to_bytes(4, const.BYTEORDER)
        nseq = (0).to_bytes(4, const.BYTEORDER)
        finalChecksum = Checksum.get_checksum(zeroedChecksum +
                                              opcode +
                                              nseq,
                                              len(opcode +
                                                  zeroedChecksum +
                                                  nseq),
                                              'sendACK')
        header = (opcode, finalChecksum, nseq)

        message = Packet.pack_file_does_not_exist_error(header)
        self.send(message)

    def receiveFileTooBigError(self):
        received_message, (serverAddres, serverPort) = self.socket.receive(
            const.STOP_FILE_TRANSFER_SIZE
        )
        opcode = received_message[:1]
        Logger.LogDebug(f"Received Error: {opcode}")
        return const.ERROR_CODE

    def checkFileMD5(self, fileName, originalMd5):
        file: bytes
        completeName = os.path.join(self.storage, fileName)
        with open(completeName, 'rb') as file:
            file = file.read()

        md5 = hashlib.md5(file)
        Logger.LogDebug(f"File server MD5: \t{md5.hexdigest()}")
        Logger.LogDebug(f"Client's MD5: \t\t{originalMd5.hex()}")

        state = bytes([const.STATE_ERROR])  # Not okay by default
        if md5.hexdigest() == originalMd5.hex():
            state = bytes([const.STATE_OK])

        return md5, state

    def closeSocket(self):
        Logger.LogSuccess(f"The transaction with {self.clientAddress}:{self.clientPort} is finished.")
        self.socket.close()
