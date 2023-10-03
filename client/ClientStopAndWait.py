import hashlib
import math
import os
import time
from common.Checksum import Checksum
from common.Logger import Logger
from common.Packet import Packet
import common.constants as const
from common.Utils import Utils


class ClientStopAndWait:
    def __init__(self):
        self.serverAddress = None
        self.serverPort = None
        self.socket = None
        self.protocolID = bytes([0x2])

    def setServerInfo(self, serverAddress, serverPort, socket):
        self.serverAddress = serverAddress
        self.serverPort = serverPort
        self.socket = socket

    def setStorage(self, storage):
        self.storage = storage

    def upload(self, filename):
        Logger.LogInfo(f"About to start uploading: {filename}")

        file: bytes
        try:
            with open(filename, 'rb') as file:
                file = file.read()
        except FileNotFoundError:
            Logger.LogError(f"File {filename} not found")
            return

        md5 = hashlib.md5(file)
        filesize = len(file)

        Logger.LogInfo("Sending (1st time) packet sendUploadRequest")
        self.sendUploadRequest(filename, filesize, md5.digest())
        firstPacketSentTime = time.time()
        communicationStarted = False
        initCommunicationSocketTimeout = 0

        chunksize = const.ERROR_CODE
        while (
                not communicationStarted) and (
                initCommunicationSocketTimeout < const.CLIENT_SOCKET_TIMEOUTS):
            try:
                self.socket.settimeout(const.TIMEOUT)
                chunksize = self.receiveFileTransferTypeResponse()
                initCommunicationSocketTimeout = 0
                communicationStarted = True
            except TimeoutError:
                initCommunicationSocketTimeout += 1
                Logger.LogWarning(
                    f"There has been a timeout (timeout number: \
                        {initCommunicationSocketTimeout}), (receiveFileTransferTypeResponse)")

            if (not communicationStarted) and (time.time() -
                                               firstPacketSentTime >
                                               const.
                                               SELECTIVE_REPEAT_PACKET_TIMEOUT
                                               ):
                self.sendUploadRequest(filename, filesize, md5.digest())
                Logger.LogInfo("Retransmiting packet sendUploadRequest")
                firstPacketSentTime = time.time()

        if chunksize == const.ERROR_CODE:
            return

        totalPackets = math.ceil(filesize / chunksize)
        Logger.LogInfo(
            f"File: {filename} - Size: {filesize} - md5: \
                {md5.hexdigest()} - Packets to send: {totalPackets}")
        self.sendFile(file, chunksize)

    def sendUploadRequest(self, fileName, fileSize, md5):
        opcode = bytes([const.UPLOAD_REQUEST_OPCODE])
        zeroedChecksum = (0).to_bytes(4, const.BYTEORDER)
        nseq = (0).to_bytes(1, const.BYTEORDER)
        finalChecksum = Checksum.get_checksum(
            zeroedChecksum + opcode + nseq,
            len(opcode + zeroedChecksum + nseq), 'sendUploadRequest')
        header = (opcode, finalChecksum, nseq)

        protocol = self.protocolID
        fileName = fileName.encode()
        payload = (
            protocol,
            fileName,
            (fileSize).to_bytes(
                16,
                const.BYTEORDER),
            md5)

        message = Packet.pack_upload_request(header, payload)
        self.send(message)

    def receiveFileTransferTypeResponse(self):

        received_message, (udpServerThreadAddress,
                           udpServerThreadPort) = \
                            self.socket.receive(
            const.FILE_TRANSFER_TYPE_RESPONSE_SIZE)

        self.serverAddress = udpServerThreadAddress
        self.serverPort = udpServerThreadPort

        opcode = int.from_bytes(received_message[:1], const.BYTEORDER)

        if opcode == const.FILE_TRANSFER_RESPONSE_OPCODE:
            header, payload = Packet.unpack_file_transfer_type_response(
                received_message)
            return payload['chunksize']
        else:
            if opcode == const.NO_DISK_SPACE_OPCODE:
                Logger.LogError(
                    'Not enough disk space in server to upload file')
            elif opcode == const.FILE_TOO_BIG_OPCODE:
                Logger.LogError('File too big, not supported by protocol')
            else:
                Logger.LogError('Uknown error, retry')

            # self.sendACK(0)
            return const.ERROR_CODE

    def sendFile(self, file, chunksize):
        fileSize = len(file)
        totalPackets = fileSize / chunksize
        packetsPushed = 0

        socketTimeouts = 0
        while (packetsPushed < totalPackets
               and socketTimeouts <
               const.CLIENT_SOCKET_TIMEOUTS):
            sequenceNumber = (packetsPushed + 1) % 2  # starts in 1
            payload = file[packetsPushed *
                           chunksize: (packetsPushed + 1) * chunksize]
            self.sendPacket(sequenceNumber, payload)
            Logger.LogDebug(f"Sent packet {sequenceNumber}")
            try:
                self.socket.settimeout(const.TIMEOUT)
                ackNseq = self.receiveACK()
                Logger.LogDebug(f"Received ACK {ackNseq}")
                socketTimeouts = 0
                packetsPushed += 1
                while (ackNseq != sequenceNumber and socketTimeouts <
                       const.CLIENT_SOCKET_TIMEOUTS):  # case 4
                    self.sendPacket(sequenceNumber, payload)
                    try:
                        self.socket.settimeout(const.TIMEOUT)
                        ackNseq = self.receiveACK()
                        Logger.LogDebug(
                            f"Re attempted: Received ACK {ackNseq}")
                        socketTimeouts = 0
                    except TimeoutError:
                        socketTimeouts += 1
                        Logger.LogWarning(
                            f"There has been a socket timeout \
                                (number: {socketTimeouts}), waiting for an ACK")
                    except BaseException:
                        Logger.LogError(
                            "There has been an error receiving the ACK")
            except TimeoutError:
                socketTimeouts += 1
                Logger.LogWarning(
                    f"There has been a socket timeout \
                        (number: {socketTimeouts}) ACK not received before timeout")
            except BaseException:
                Logger.LogError("There has been an error receiving the ACK")

            # Case 1: Packet received => ACK received
            # Case 2: Packet lost => timeout => do nothing (resend)
            # Case 3: Packet received, ACK lost =>
            # timeout => do nothing (resend)
            # Case 4: ACK not received before timeout => timeout => resend
            # packet => receive ack1 twice (resend next packet)

        self.stopUploading(int(totalPackets + 1))

        print('File transfer has ended.')

    def sendPacket(self, nseq, payload):
        opcode = bytes([const.PACKET_OPCODE])
        zeroedChecksum = (0).to_bytes(4, const.BYTEORDER)
        nseqToBytes = (nseq).to_bytes(4, const.BYTEORDER)

        # Checksum has to go first, for alignment and calculation
        finalChecksum = Checksum.get_checksum(
            zeroedChecksum + opcode + nseqToBytes, len(
                opcode + zeroedChecksum + nseqToBytes), 'sendPackage')

        header = (opcode, finalChecksum, nseqToBytes)
        message = Packet.pack_package(header, payload)
        Logger.LogInfo(f"About to send packet nseq: {nseq}")
        self.send(message)

    def send(self, message):
        self.socket.send(message, self.serverAddress, self.serverPort)

    def receiveACK(self):
        received_message, _ = self.socket.receive(const.ACK_SIZE)
        header = Packet.unpack_ack(received_message)
        return header['nseq']

    def stopUploading(self, nseq):
        self.socket.settimeout(None)
        received_message, (serverAddres, serverPort) = self.socket.receive(
            const.STOP_FILE_TRANSFER_SIZE)

        header, payload = Packet.unpack_stop_file_transfer(received_message)
        Logger.LogInfo(f"Received ACK: {header['nseq']}")

        if payload["state"] == 0:
            Logger.LogError(
                "There's been an error uploading the file in \
                    the server. File corrupt in the server")

        opcode = bytes([const.FINAL_ACK_OPCODE])
        zeroedChecksum = (0).to_bytes(4, const.BYTEORDER)
        nseqToBytes = (header['nseq']).to_bytes(4, const.BYTEORDER)
        finalChecksum = Checksum.get_checksum(
            zeroedChecksum + opcode + nseqToBytes, len(
                opcode + zeroedChecksum + nseqToBytes), 'stopUploading')
        header = (opcode, finalChecksum, nseqToBytes)

        message = Packet.pack_ack(header)

        self.send(message)

        print('Finalized uploading file.')

    def download(self, fileName):
        initCommunicationSocketTimeout = 0
        communicationStarted = False
        md5 = None
        Logger.LogInfo(f"About to start downloading: {fileName}")
        Logger.LogInfo("Sending (1st time) packet sendDownloadRequest")

        self.sendDownloadRequest(fileName)
        firstPacketSentTime = time.time()
        errorCode = False
        while (
                not communicationStarted) and (
                initCommunicationSocketTimeout < const.CLIENT_SOCKET_TIMEOUTS
                ) and not errorCode:
            try:
                self.socket.settimeout(const.TIMEOUT)
                opcode, fileSize, md5 = self.receiveDownloadResponse()
                initCommunicationSocketTimeout = 0
                communicationStarted = True
                if fileSize >= Utils.getFreeDiskSpace():
                    errorCode = True
                else:
                    if opcode == const.FILE_DOES_NOT_EXIST_OPCODE:
                        Logger.LogError(f"File {fileName} does not \
                                        exist in the server")
                        self.sendACK(0)
                        return
                    if opcode != const.DOWNLOAD_REQUEST_RESPONSE_OPCODE:
                        Logger.LogError("Unknown error")
                        return
            except TimeoutError:
                initCommunicationSocketTimeout += 1
                Logger.LogWarning(
                    f"There has been a timeout \
                        (timeout number: {initCommunicationSocketTimeout})")

            if (not communicationStarted) and (time.time() -
                                               firstPacketSentTime >
                                               const.
                                               SELECTIVE_REPEAT_PACKET_TIMEOUT
                                               ):
                Logger.LogInfo("Retransmiting packet sendDownloadRequest")
                self.sendDownloadRequest(fileName)
                firstPacketSentTime = time.time()

        Logger.LogDebug(
            f"You are about to download a file of \
                {fileSize} bytes and with an md5 of {md5}")

        if errorCode:
            Logger.LogError(f"Not enough space for download. \
                            {fileSize/1000}kB are needed")
            self.sendNoDiskSpaceError()
            errorSentTime = time.time()
            errorTimeouts = 0
            Logger.LogDebug("Sent error")
            receivedErrorACK = False
            while (errorTimeouts < const.LAST_ACK_PACKET_TIMEOUT
                    and not receivedErrorACK):
                try:
                    self.socket.settimeout(const.TIMEOUT)
                    ackNseq = self.receiveACK()
                    Logger.LogDebug(f"Received ACK {ackNseq}")
                    errorTimeouts = 0
                    receivedErrorACK = True
                except TimeoutError:
                    Logger.LogWarning(f"There has been a timeout on \
                                    the servers ACK for an error \
                                    (timeout number: {errorTimeouts})")
                    errorTimeouts += 1

                if (not communicationStarted) and (
                    time.time() - errorSentTime >
                    const.SELECTIVE_REPEAT_PACKET_TIMEOUT
                ):
                    self.sendNoDiskSpaceError()
                    errorSentTime = time.time()
            return

        self.sendConnectionACK()
        packetSentTime = time.time()
        sendConnectionACKSocketTimeout = 0
        firstPacketArrived = False
        header = None
        payload = None

        while (not firstPacketArrived) and (
            sendConnectionACKSocketTimeout
                < const.CLIENT_SOCKET_TIMEOUTS):
            try:
                self.socket.settimeout(const.TIMEOUT)
                header, payload = self.receivePacket()
                firstPacketArrived = True
                sendConnectionACKSocketTimeout = 0
                Logger.LogDebug("Received first packet")
            except TimeoutError:
                sendConnectionACKSocketTimeout += 1
                Logger.LogWarning(f"There has been a timeout \
                    (timeout number: {sendConnectionACKSocketTimeout})")

            if (not firstPacketArrived) and (
                time.time() - packetSentTime
                    > const.SELECTIVE_REPEAT_PACKET_TIMEOUT):
                self.sendConnectionACK()
                packetSentTime = time.time()

        file = []
        totalPackets = math.ceil(fileSize / const.CHUNKSIZE)
        acksSent = 0
        nextNseq = 1
        firstIteration = True
        # enviar ok al servidor para que arranque la descarga
        self.socket.settimeout(None)
        while acksSent < totalPackets:
            if not firstIteration:
                header, payload = self.receivePacket()
                Logger.LogDebug(f"Received packet with nseq: {header['nseq']}")
            else:
                firstIteration = False
            if header is not None and header['nseq'] == nextNseq:
                if self.isChecksumOK(header, payload):
                    self.sendACK(header['nseq'])
                    Logger.LogDebug(f"Sent ACK {header['nseq']}")
                    file.append(payload)
                    nextNseq = acksSent % 2
                    acksSent += 1
            else:  # client resends packet - cases 3 (lost ACK) and 4 (timeout)
                self.sendACK(header['nseq'])
                # server only resends ACK (detects duplicate)
                Logger.LogDebug(f"RE-Sent ACK {header['nseq']}")

        bytesInLatestPacket = fileSize % const.CHUNKSIZE
        Logger.LogWarning(
            f"There are {bytesInLatestPacket} \
                bytes on the last packet. removing padding")
        file[len(file) - 1] = file[len(file) - 1][0:bytesInLatestPacket]
        Logger.LogWarning("Padding removed")

        self.saveFile(file, fileName)
        newMd5, state = self.checkFileMD5(fileName, md5)
        self.stopFileTransfer(nextNseq, fileName, newMd5, state)

    def isChecksumOK(self, header, payload):
        opcode = header['opcode'].to_bytes(1, const.BYTEORDER)
        checksum = (header['checksum']).to_bytes(4, const.BYTEORDER)
        nseqToBytes = header['nseq'].to_bytes(4, const.BYTEORDER)

        return Checksum.is_checksum_valid(
            checksum + opcode + nseqToBytes,
            len(opcode + checksum + nseqToBytes)
        )

    def sendDownloadRequest(self, fileName):
        opcode = bytes([const.DOWNLOAD_REQUEST_OPCODE])
        zeroedChecksum = (0).to_bytes(4, const.BYTEORDER)
        nseq = (0).to_bytes(1, const.BYTEORDER)
        finalChecksum = Checksum.get_checksum(
            zeroedChecksum + opcode + nseq,
            len(opcode + zeroedChecksum + nseq),
            'sendDownloadRequest')
        header = (opcode, finalChecksum, nseq)

        protocol = self.protocolID
        fileName = fileName.encode()
        payload = (
            protocol,
            fileName)
        message = Packet.pack_download_request(header, payload)
        self.send(message)

    def receiveDownloadResponse(self):
        received_message, (udpServerThreadAddress,
                           udpServerThreadPort) = self.socket.receive(
            const.DOWNLOAD_RESPONSE_SIZE)

        self.serverAddress = udpServerThreadAddress
        self.serverPort = udpServerThreadPort

        if Utils.bytesToInt(
                received_message[:1]) == const.FILE_DOES_NOT_EXIST_OPCODE:
            return const.FILE_DOES_NOT_EXIST_OPCODE, 0, 0
        elif Utils.bytesToInt(received_message[:1]) == \
                const.\
                DOWNLOAD_REQUEST_RESPONSE_OPCODE:
            Logger.LogDebug("Received download response")
            _, payload = Packet.unpack_download_response(received_message)
            return Utils.bytesToInt(
                received_message[:1]), payload['filesize'], payload['md5']
        else:
            return const.ERROR_CODE, 0, 0

    def receivePacket(self):
        received_message, (serverAddres, serverPort) = self.socket.receive(
            const.PACKET_SIZE)

        if Utils.bytesToInt(received_message[:1]) == 0:
            header, payload = Packet.unpack_upload_request(received_message)
        else:
            header, payload = Packet.unpack_package(received_message)

        return header, payload

    def sendConnectionACK(self):
        opcode = bytes([const.INIT_DOWNLOAD_ACK_OPCODE])
        zeroedChecksum = (0).to_bytes(4, const.BYTEORDER)
        nseqToBytes = (0).to_bytes(4, const.BYTEORDER)
        finalChecksum = Checksum.get_checksum(
            zeroedChecksum + opcode + nseqToBytes, len(
                opcode + zeroedChecksum + nseqToBytes), 'sendACK')
        header = (opcode, finalChecksum, nseqToBytes)
        message = Packet.pack_ack(header)
        Logger.LogInfo("Sending Connection ACK")
        self.send(message)

    def sendACK(self, nseq):
        opcode = bytes([const.ACK_OPCODE])
        zeroedChecksum = (0).to_bytes(4, const.BYTEORDER)
        nseqToBytes = nseq.to_bytes(4, const.BYTEORDER)
        finalChecksum = Checksum.get_checksum(
            zeroedChecksum + opcode + nseqToBytes, len(
                opcode + zeroedChecksum + nseqToBytes), 'sendACK')
        header = (opcode, finalChecksum, nseqToBytes)
        message = Packet.pack_ack(header)
        Logger.LogInfo(f"Sending ACK {nseq} ")
        self.send(message)

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

    def saveFile(self, file, fileName):
        completeName = os.path.join(self.storage, fileName)
        os.makedirs(os.path.dirname(completeName), exist_ok=True)

        fileWriter = open(completeName, "wb")
        for i in range(0, len(file)):
            fileWriter.write(file[i])

        Logger.LogInfo(f"File written into: {completeName}")
        fileWriter.close()

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

    def sendNoDiskSpaceError(self):
        opcode = bytes([const.NO_DISK_SPACE_OPCODE])
        zeroedChecksum = (0).to_bytes(4, const.BYTEORDER)
        nseqToBytes = (0).to_bytes(4, const.BYTEORDER)
        finalChecksum = Checksum.get_checksum(
            zeroedChecksum + opcode + nseqToBytes,
            len(opcode + zeroedChecksum + nseqToBytes), 'sendACK'
        )
        header = (opcode, finalChecksum, nseqToBytes)
        message = Packet.pack_file_too_big_error(header)
        self.send(message)
