from common.Checksum import get_checksum, is_checksum_valid
from common.Logger import LogInfo, LogWarning, LogError, LogDebug
from tqdm import tqdm
import hashlib
import math
import time
import os
from common.Packet import Packet
from common.Utils import Utils
from common.constants import CHUNKSIZE, CLIENT_SOCKET_TIMEOUTS, \
    SELECTIVE_REPEAT_PACKET_TIMEOUT, UPLOAD_REQUEST_OPCODE, BYTEORDER, \
    FILE_TRANSFER_TYPE_RESPONSE_SIZE, NO_DISK_SPACE_OPCODE, STATE_OK, \
    STATE_ERROR, STOP_FILE_TRANSFER_OPCODE, INIT_DOWNLOAD_ACK_OPCODE, \
    ACK_OPCODE, PACKET_SIZE, DOWNLOAD_RESPONSE_SIZE, \
    STOP_FILE_TRANSFER_SIZE, PACKET_OPCODE, ACK_SIZE, FINAL_ACK_OPCODE


class ClientSelectiveRepeat:

    def __init__(self):
        self.serverAddress = None
        self.serverPort = None
        self.socket = None
        self.protocolID = bytes([0x1])
        self.window = []
        self.chunksize = None
        self.storage = None

    def setServerInfo(self, serverAddress, serverPort, socket):
        self.serverAddress = serverAddress
        self.serverPort = serverPort
        self.socket = socket

    def setStorage(self, storage):
        self.storage = storage

    def send(self, message):
        self.socket.send(message, self.serverAddress, self.serverPort)

    def upload(self, filename):
        self.window = []
        initCommunicationSocketTimeout = 0
        communicationStarted = False

        try:
            file: bytes
            with open(filename, 'rb') as file:
                file = file.read()

            md5 = hashlib.md5(file)
            filesize = len(file)
            totalPackets = math.ceil(filesize / CHUNKSIZE)

            LogInfo(
                f"File: {filename} - Size: {filesize} - md5: {md5.hexdigest()}\
                - Packets to send: {totalPackets}")

            self.sendUploadRequest(filename, filesize, md5.digest())
            firstPacketSentTime = time.time()

            errorCode = False
            while (
                    not communicationStarted) and (
                    initCommunicationSocketTimeout < CLIENT_SOCKET_TIMEOUTS):
                try:
                    self.socket.settimeout(0.2)
                    receivedMessageHeader, receivedMessagePayload = \
                        self.receiveFileTransferTypeResponse()
                    if (receivedMessageHeader['opcode']) == 13:
                        self.sendACK(0)
                        errorCode = True
                    initCommunicationSocketTimeout = 0
                    communicationStarted = True
                except TimeoutError:
                    initCommunicationSocketTimeout += 1
                    LogWarning(
                        f"There has been a timeout (timeout number: \
                            {initCommunicationSocketTimeout})")

                if (not communicationStarted) and \
                        (time.time() -
                            firstPacketSentTime >
                            SELECTIVE_REPEAT_PACKET_TIMEOUT):
                    self.sendUploadRequest(filename, filesize, md5.digest())
                    firstPacketSentTime = time.time()

            if not errorCode:
                LogInfo(f"Total de paquetes a enviar {totalPackets}")
                packetsACKed = 0
                packetsPushed = 0
                nseq = 1
                payloadWithNseq = {}
                socketTimeouts = 0

                while (
                        packetsACKed != totalPackets) and (
                        socketTimeouts < CLIENT_SOCKET_TIMEOUTS):
                    for i in tqdm(
                            range(totalPackets),
                            desc="Uploading...",
                            ascii=False,
                            ncols=75):
                        while ((len(self.window) != 10) and (
                                packetsPushed != totalPackets)):
                            payloadAux = file[packetsPushed * CHUNKSIZE:
                                              (packetsPushed + 1) * CHUNKSIZE]
                            payloadWithNseq[nseq] = payloadAux
                            self.window.append(
                                {'nseq': nseq, 'isSent': False,
                                 'isACKed': False, 'sentAt': None})
                            packetsPushed += 1
                            nseq += 1

                        for e in self.window:
                            if not e['isSent']:
                                LogDebug(
                                    f"Sending packet with sequence: \
                                        {e['nseq']}")
                                self.sendPackage(
                                    payloadWithNseq[e['nseq']], e['nseq'])
                                e['sentAt'] = time.time()
                                e['isSent'] = True

                        ackReceived = None

                        try:
                            self.socket.settimeout(0.2)
                            ackReceived = self.receiveACK()
                            socketTimeouts = 0
                        except TimeoutError:
                            socketTimeouts += 1
                            LogWarning(
                                f"There has been a socket timeout (number: \
                                    {socketTimeouts})")
                        except BaseException:
                            LogError(
                                "There has been an error receiving the ACK")

                        for e in self.window:

                            if (not e['isACKed']) and ackReceived == e['nseq']:
                                e['isACKed'] = True
                                packetsACKed += 1
                                LogDebug(
                                    f"ACKed {packetsACKed} packets")
                            if (not e['isACKed']) and (
                                    time.time() - e['sentAt'] >
                                    SELECTIVE_REPEAT_PACKET_TIMEOUT):
                                if (e['nseq'] != totalPackets):
                                    self.sendPackage(
                                        payloadWithNseq[e['nseq']], e['nseq'])
                                else:
                                    self.sendLastPackage(
                                        payloadWithNseq[e['nseq']], e['nseq'])
                                e['sentAt'] = time.time()

                        if self.window[0]['isACKed']:
                            LogDebug("Moving window")
                            self.moveSendWindow()

                print("Verifying file...")
                self.stopUploading(int(totalPackets + 1))

                print('File transfer has completed.')

            else:
                LogError("The transaction could not be completed \
                         because the server has not enough space \
                         to allocate the file")

        except FileNotFoundError:
            LogError("The file does not exist. You can't upload it.")

    def sendUploadRequest(self, fileName, fileSize, md5):
        opcode = bytes([UPLOAD_REQUEST_OPCODE])
        zeroedChecksum = (0).to_bytes(4, BYTEORDER)
        nseq = (0).to_bytes(1, BYTEORDER)
        finalChecksum = get_checksum(
            zeroedChecksum + opcode + nseq,
            len(opcode + zeroedChecksum + nseq), 'sendUploadRequest')
        header = (opcode, finalChecksum, nseq)

        protocol = self.protocolID
        fileName = fileName.encode()
        payload = (protocol, fileName, (fileSize).to_bytes(16, BYTEORDER), md5)

        message = Packet.pack_upload_request(header, payload)
        self.send(message)

    def receiveFileTransferTypeResponse(self):
        received_message, (udpServerThreadAddress,
                           udpServerThreadPort) = self.socket.receive(
            FILE_TRANSFER_TYPE_RESPONSE_SIZE)

        self.serverAddress = udpServerThreadAddress
        self.serverPort = udpServerThreadPort

        if Utils.bytesToInt(received_message[:1]) == 13:
            header, payload = Packet.unpack_error_message(received_message)
        else:
            header, payload = Packet.unpack_file_transfer_type_response(
                received_message)
            self.chunksize = payload['chunksize']

        return header, payload

    def sendPackage(self, payload, nseq):
        opcode = bytes([PACKET_OPCODE])
        zeroedChecksum = (0).to_bytes(4, BYTEORDER)
        nseqToBytes = (nseq).to_bytes(4, BYTEORDER)

        # Checksum has to go first, for alignment and calculation
        finalChecksum = get_checksum(
            zeroedChecksum + opcode + nseqToBytes, len(
                opcode + zeroedChecksum + nseqToBytes), 'sendPackage')

        header = (opcode, finalChecksum, nseqToBytes)
        message = Packet.pack_package(header, payload)
        LogInfo(f"About to send packet nseq: {nseq}")
        self.send(message)

    def receiveACK(self):
        received_message, (serverAddres,
                           serverPort) = self.socket.receive(ACK_SIZE)

        header = Packet.unpack_ack(received_message)
        LogInfo(f"RECEIVED ACK. \t{header}")
        opcode = header['opcode'].to_bytes(1, BYTEORDER)
        checksum = (header['checksum']).to_bytes(4, BYTEORDER)
        nseqToBytes = header['nseq'].to_bytes(4, BYTEORDER)

        if is_checksum_valid(
                checksum + opcode + nseqToBytes,
                len(opcode + checksum + nseqToBytes)):
            return header['nseq']
        else:
            LogWarning("Invalid checksum for ACK receeived")
            return header['nseq']

    def moveSendWindow(self):
        while len(self.window) != 0 and self.window[0]['isACKed']:
            self.window.pop(0)

    def stopUploading(self, nseq):
        self.socket.settimeout(None)
        received_message, (serverAddres, serverPort) = self.socket.receive(
            STOP_FILE_TRANSFER_SIZE)

        header, payload = Packet.unpack_stop_file_transfer(received_message)

        if payload["state"] == 0:
            LogError(
                "There's been an error uploading the file \
                in the server. File corrupt in the server")

        opcode = bytes([FINAL_ACK_OPCODE])
        zeroedChecksum = (0).to_bytes(4, BYTEORDER)
        nseqToBytes = (header['nseq']).to_bytes(4, BYTEORDER)
        finalChecksum = get_checksum(
            zeroedChecksum + opcode + nseqToBytes, len(
                opcode + zeroedChecksum + nseqToBytes), 'stopUploading')
        header = (opcode, finalChecksum, nseqToBytes)

        message = Packet.pack_ack(header)

        self.send(message)

        print('Finalized uploading file')

    def sendLastPackage(self, payload, nseq):
        opcode = bytes([0x4])

        checksum = (2).to_bytes(4, BYTEORDER)

        nseqToBytes = nseq.to_bytes(4, BYTEORDER)
        header = (opcode, checksum, nseqToBytes)

        message = Packet.pack_package(header, payload)
        self.send(message)

    def download(self, filename):
        self.window = []
        initCommunicationSocketTimeout = 0
        communicationStarted = False
        errorCode = False

        self.sendDownloadRequest(filename)
        firstPacketSentTime = time.time()

        filesize = None
        md5 = None

        while (
                not communicationStarted) and (
                initCommunicationSocketTimeout < CLIENT_SOCKET_TIMEOUTS):
            try:
                self.socket.settimeout(0.2)
                receivedMessageHeader, receivedMessagePayload \
                    = self.receiveDownloadResponse()
                if (receivedMessageHeader['opcode']) == 12:
                    self.sendACK(0)
                    errorCode = True
                initCommunicationSocketTimeout = 0
                communicationStarted = True
            except TimeoutError:
                initCommunicationSocketTimeout += 1
                LogWarning(
                    f"There has been a timeout (timeout number: \
                        {initCommunicationSocketTimeout})")

            if (not communicationStarted) and (time.time() -
                                               firstPacketSentTime >
                                               SELECTIVE_REPEAT_PACKET_TIMEOUT
                                               ):
                self.sendDownloadRequest(filename)
                firstPacketSentTime = time.time()

        if not errorCode:
            filesize = receivedMessagePayload['filesize']

            if not self.isFileSizeOk(filesize):
                LogError(
                    f"Not enough space for download \
                        {filesize/1000}kB are needed")
                self.sendNoDiskSpaceErrorPacket()
                return

            md5 = receivedMessagePayload['md5']

            LogDebug(
                f"You are about to download a file of \
                    {filesize} bytes and with an md5 of {md5}")

            self.sendConnectionACK()
            sendConnectionACKSocketTimeout = 0
            firstPacketArrived = False
            packetSentTime = time.time()

            header = None
            payload = None

            while (
                    not firstPacketArrived) and (
                    sendConnectionACKSocketTimeout < CLIENT_SOCKET_TIMEOUTS):
                try:
                    self.socket.settimeout(0.2)
                    header, header = self.receivePacket()
                    sendConnectionACKSocketTimeout = 0
                    firstPacketArrived = True
                except TimeoutError:
                    sendConnectionACKSocketTimeout += 1
                    LogWarning(
                        f"There has been a timeout (timeout number: \
                            {sendConnectionACKSocketTimeout})")

                if (not firstPacketArrived) and \
                    (time.time() -
                     packetSentTime > SELECTIVE_REPEAT_PACKET_TIMEOUT):
                    self.sendConnectionACK(filename)
                    packetSentTime = time.time()

            fileNameModified = filename.rstrip('\x00')
            file = {}
            totalPackets = math.ceil(filesize / CHUNKSIZE)
            distinctAcksSent = 0
            firstIteration = True

            for i in range(1, 10):
                self.window.append({'nseq': i, 'isACKSent': False})

            while distinctAcksSent != totalPackets:
                if not firstIteration:
                    header, payload = self.receivePacket()
                else:
                    firstIteration = False

                if header is not None and self.isChecksumOK(header, payload):
                    self.sendACK(header['nseq'])

                for e in self.window:
                    if header is not None and (
                            not e['isACKSent']) and \
                                header['nseq'] == e['nseq']:
                        e['isACKSent'] = True
                        distinctAcksSent += 1
                        file[header['nseq'] - 1] = payload

                if header is not None and header['nseq'] \
                        == self.window[0]['nseq']:
                    self.moveReceiveWindow()

            bytesInLatestPacket = filesize % CHUNKSIZE
            LogWarning(
                "There are {bytesInLatestPacket} \
                   bytes on the las packet. removing padding")
            file[len(file) - 1] = \
                file[len(file) - 1][0:bytesInLatestPacket]
            LogWarning("Padding removed")
            self.saveFile(file, fileNameModified)

            self.stopFileTransfer(totalPackets + 1, fileNameModified, md5)

            print('File transfer has ended.')

        else:
            LogError(
                "The file does not exist in the \
                    server. You can't download it.")

    def sendDownloadRequest(self, fileName):
        opcode = bytes([0x2])
        zeroedChecksum = (0).to_bytes(4, BYTEORDER)
        nseq = (0).to_bytes(1, BYTEORDER)
        finalChecksum = get_checksum(
            zeroedChecksum + opcode + nseq,
            len(opcode + zeroedChecksum + nseq), 'sendDownloadRequest')
        header = (opcode, finalChecksum, nseq)

        protocol = self.protocolID
        fileName = fileName.encode()
        payload = (protocol, fileName)

        message = Packet.pack_download_request(header, payload)
        self.send(message)

    def receiveDownloadResponse(self):
        received_message, (udpServerThreadAddress,
                           udpServerThreadPort) = self.socket.receive(
            DOWNLOAD_RESPONSE_SIZE)

        self.serverAddress = udpServerThreadAddress
        self.serverPort = udpServerThreadPort

        if Utils.bytesToInt(received_message[:1]) == 12:
            header, payload = Packet.unpack_error_message(received_message)
        else:
            header, payload = Packet.unpack_download_response(received_message)

        return header, payload

    def receivePacket(self):
        received_message, (serverAddres, serverPort) = self.socket.receive(
            PACKET_SIZE)

        if Utils.bytesToInt(received_message[:1]) == 0:
            header, payload = Packet.unpack_upload_request(received_message)
        else:
            header, payload = Packet.unpack_package(received_message)

        return header, payload

    def moveReceiveWindow(self):
        while len(self.window) != 0 and self.window[0]['isACKSent']:
            lastNseq = self.window[-1]['nseq']
            self.window.pop(0)
            self.window.append({'nseq': lastNseq + 1, 'isACKSent': False})

    def isChecksumOK(self, header, payload):
        opcode = header['opcode'].to_bytes(1, BYTEORDER)
        checksum = (header['checksum']).to_bytes(4, BYTEORDER)
        nseqToBytes = header['nseq'].to_bytes(4, BYTEORDER)

        return is_checksum_valid(
            checksum + opcode + nseqToBytes,
            len(opcode + checksum + nseqToBytes))

    def sendACK(self, nseq):
        opcode = bytes([ACK_OPCODE])
        zeroedChecksum = (0).to_bytes(4, BYTEORDER)
        nseqToBytes = nseq.to_bytes(4, BYTEORDER)
        finalChecksum = get_checksum(
            zeroedChecksum + opcode + nseqToBytes, len(
                opcode + zeroedChecksum + nseqToBytes), 'sendACK')
        header = (opcode, finalChecksum, nseqToBytes)
        message = Packet.pack_ack(header)
        LogInfo(f"Sending ACK {nseq} ")
        self.send(message)

    def sendConnectionACK(self):
        opcode = bytes([INIT_DOWNLOAD_ACK_OPCODE])
        zeroedChecksum = (0).to_bytes(4, BYTEORDER)
        nseqToBytes = (0).to_bytes(4, BYTEORDER)
        finalChecksum = get_checksum(
            zeroedChecksum + opcode + nseqToBytes, len(
                opcode + zeroedChecksum + nseqToBytes), 'sendACK')
        header = (opcode, finalChecksum, nseqToBytes)
        message = Packet.pack_ack(header)
        LogInfo("Sending Connection ACK")
        self.send(message)

    def saveFile(self, file, fileName):
        completeName = os.path.join(self.storage, fileName)
        os.makedirs(os.path.dirname(completeName), exist_ok=True)

        fileWriter = open(completeName, "wb")
        for i in range(0, len(file)):
            fileWriter.write(file[i])

        LogInfo(f"File written into: {completeName}")
        fileWriter.close()

    def stopFileTransfer(self, nseq, fileName, originalMd5):
        opcode = bytes([STOP_FILE_TRANSFER_OPCODE])
        zeroedChecksum = (0).to_bytes(4, BYTEORDER)
        nseqToBytes = nseq.to_bytes(4, BYTEORDER)
        finalChecksum = get_checksum(
            zeroedChecksum + opcode + nseqToBytes, len(
                opcode + zeroedChecksum + nseqToBytes), 'sendACK')
        header = (opcode, finalChecksum, nseqToBytes)

        file: bytes
        completeName = os.path.join(self.storage, fileName)
        with open(completeName, 'rb') as file:
            file = file.read()

        md5 = hashlib.md5(file)
        LogDebug(f"File client MD5: \t{md5.hexdigest()}")
        LogDebug(f"Server's MD5: \t\t{originalMd5.hex()}")

        state = bytes([STATE_ERROR])  # Not okay by default
        if md5.hexdigest() == originalMd5.hex():
            state = bytes([STATE_OK])

        payload = (md5.digest(), state)
        message = Packet.pack_stop_file_transfer(header, payload)

        self.send(message)

    def isFileSizeOk(self, filesize):
        return filesize <= Utils.getFreeDiskSpace()

    def sendNoDiskSpaceErrorPacket(self):
        opcode = bytes([NO_DISK_SPACE_OPCODE])
        zeroedChecksum = (0).to_bytes(4, BYTEORDER)
        nseqToBytes = (0).to_bytes(4, BYTEORDER)
        finalChecksum = get_checksum(
            zeroedChecksum + opcode + nseqToBytes, len(
                opcode + zeroedChecksum + nseqToBytes), 'sendACK')
        header = (opcode, finalChecksum, nseqToBytes)

        message = Packet.pack_ack(header)
        LogInfo("Sending not enough space error.")

        self.send(message)
