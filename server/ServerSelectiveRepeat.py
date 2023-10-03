import hashlib
import os
import math
import time
from common.Packet import Packet
from common.Utils import Utils
from common.constants import SELECTIVE_REPEAT, \
    FILE_TRANSFER_RESPONSE_OPCODE, BYTEORDER, CHUNKSIZE, \
    CLIENT_SOCKET_TIMEOUTS, SELECTIVE_REPEAT_PKT_TOUT, \
    DOWNLOAD_REQUEST_RESPONSE_OPCODE, DOWNLOAD_REQUEST_OPCODE, \
    NO_DISK_SPACE_OPCODE, ACK_SIZE, PACKET_SIZE, ACK_OPCODE, \
    STOP_FILE_TRANSFER_OPCODE, STATE_OK, STATE_ERROR, \
    FILE_DOES_NOT_EXIST_OPCODE, LAST_ACK_PACKET_TIMEOUT, \
    STOP_FILE_TRANSFER_SIZE, TIMEOUT, FINAL_ACK_OPCODE, \
    SELECTIVE_REPEAT_PACKET_TIMEOUT
from common.Logger import Logger
from common.Checksum import Checksum


class ServerSelectiveRepeat:

    def __init__(self, socket, clientAddress, clientPort, storage):
        self.socket = socket
        self.clientAddress = clientAddress
        self.clientPort = clientPort
        self.protocolID = bytes([SELECTIVE_REPEAT])
        self.window = []
        self.storage = storage

    def send(self, message):
        self.socket.send(message, self.clientAddress, self.clientPort)

    def sendFileTransferTypeResponse(self):
        opcode = bytes([FILE_TRANSFER_RESPONSE_OPCODE])
        zeroedChecksum = (0).to_bytes(4, BYTEORDER)
        nseq = (0).to_bytes(4, BYTEORDER)
        finalChecksum = Checksum.get_checksum(
            zeroedChecksum + opcode + nseq,
            len(opcode + zeroedChecksum + nseq), 'sendACK')

        header = (opcode, finalChecksum, nseq)

        # fixed chunksize (4096 bytes)
        chunksize = CHUNKSIZE.to_bytes(4, BYTEORDER)

        message = Packet.pack_file_transfer_type_response(header, chunksize)

        self.send(message)

        nextPacketIsADataPacket = False

        receivedPacketHeader, receivedPacketPayload = self.receivePackage()

        while not nextPacketIsADataPacket:
            if receivedPacketHeader['opcode'] == 0:
                self.send(message)
                receivedPacketHeader, \
                    receivedPacketPayload = self.receivePackage()
            else:
                nextPacketIsADataPacket = True

        return receivedPacketHeader, receivedPacketPayload

    def upload(self, filesize, fileName, originalMd5):
        if filesize >= Utils.getFreeDiskSpace():
            noDiskSpacePacketTimeout = 0
            noDiskSpacePacketACKed = False
            noDiskSpacePacketSentTime = time.time()
            self.sendNoDiskSpaceErrorPacket()

            while (
                    not noDiskSpacePacketACKed) and (
                    noDiskSpacePacketTimeout < CLIENT_SOCKET_TIMEOUTS):
                try:
                    self.socket.settimeout(TIMEOUT)
                    nseq = self.receiveACK()
                    if nseq == 0:
                        noDiskSpacePacketTimeout = 0
                        noDiskSpacePacketACKed = True
                except TimeoutError:
                    noDiskSpacePacketTimeout += 1

                if (not noDiskSpacePacketACKed) and (time.time() -
                                                     noDiskSpacePacketSentTime
                                                     >
                                                     SELECTIVE_REPEAT_PKT_TOUT
                                                     ):
                    Logger.LogWarning(
                        f"There has been a timeout in Seending \
                            No Disk Error Packet)")
                    self.sendNoDiskSpaceErrorPacket()
                    noDiskSpacePacketSentTime = time.time()

            Logger.LogError(
                f"Not enough space for download {filesize/1000}kB are needed")

        else:
            self.window = []
            fileName = fileName.rstrip('\x00')
            header, payload = self.sendFileTransferTypeResponse()
            file = {}
            totalPackets = math.ceil(filesize / CHUNKSIZE)
            distinctAcksSent = 0
            firstIteration = True
            acksSent = {}
            Logger.LogInfo(f"Total packets to send: {totalPackets}")

            while distinctAcksSent != totalPackets:
                if not firstIteration:
                    self.socket.settimeout(None)
                    header, payload = self.receivePackage()
                else:
                    firstIteration = False
                if self.isChecksumOK(header, payload):
                    self.sendACK(header['nseq'])
                    acksSent[header['nseq']] = True
                    file[header['nseq'] - 1] = payload

                distinctAcksSent = len(acksSent)

                print(f"{distinctAcksSent} vs {totalPackets}")


            bytesInLatestPacket = filesize % CHUNKSIZE
            Logger.LogWarning(
                f"There are {bytesInLatestPacket} \
                    bytes on the last packet. removing padding")
            file[len(file) - 1] = file[len(file) - 1][0:bytesInLatestPacket]
            Logger.LogWarning("Padding removed")
            self.saveFile(file, fileName)

            self.stopFileTransfer(totalPackets + 1, fileName, originalMd5, totalPackets)

            print('Finalized uploading file')

    def download(self, filename):
        self.window = []
        filename = filename.rstrip('\x00')
        file: bytes
        completeName = os.path.join(self.storage, filename)

        try:
            Logger.LogInfo(f"Download request for file: {completeName}")
            with open(completeName, 'rb') as file:
                file = file.read()

            errorCode = self.sendDownloadRequestResponse(file)

            if not errorCode:
                md5 = hashlib.md5(file)
                filesize = len(file)
                totalPackets = math.ceil(filesize / CHUNKSIZE)

                Logger.LogInfo(
                    f"File: {filename} - Size: {filesize} - md5: \
                        {md5.hexdigest()} - Packets to send: {totalPackets}")

                packetsACKed = 0
                packetsPushed = 0
                nseq = 1
                payloadWithNseq = {}
                socketTimeouts = 0

                while (
                        packetsACKed != totalPackets) and (
                        socketTimeouts < CLIENT_SOCKET_TIMEOUTS):
                    while ((len(self.window) != 10) and (
                            packetsPushed != totalPackets)):
                        payloadAux = file[packetsPushed *
                                          CHUNKSIZE: (packetsPushed + 1)
                                          * CHUNKSIZE]
                        payloadWithNseq[nseq] = payloadAux
                        self.window.append(
                            {'nseq': nseq, 'isSent': False,
                             'isACKed': False, 'sentAt': None})
                        packetsPushed += 1
                        nseq += 1

                    for e in self.window:
                        if not e['isSent']:
                            Logger.LogDebug(
                                f"Sending packet with sequence: {e['nseq']}")
                            self.sendPackage(
                                payloadWithNseq[e['nseq']], e['nseq'])
                            e['sentAt'] = time.time()
                            e['isSent'] = True

                    ackReceived = None

                    try:
                        self.socket.settimeout(TIMEOUT)
                        ackReceived = self.receiveACK()
                        socketTimeouts = 0
                    except TimeoutError:
                        socketTimeouts += 1
                        Logger.LogWarning(
                            f"There has been a socket timeout \
                            (number: {socketTimeouts})")
                    except BaseException:
                        Logger.LogError(
                            "There has been an error receiving the ACK")

                    for e in self.window:
                        if (not e['isACKed']) and ackReceived == e['nseq']:
                            e['isACKed'] = True
                            packetsACKed += 1
                            Logger.LogDebug(f"ACKed {packetsACKed} packets")
                        if (not e['isACKed']) and (time.time() -
                                e['sentAt'] >
                                SELECTIVE_REPEAT_PACKET_TIMEOUT):
                            self.sendPackage(
                                payloadWithNseq[e['nseq']], e['nseq'])
                            e['sentAt'] = time.time()

                    if self.window[0]['isACKed']:
                        Logger.LogDebug("Moving window")
                        self.moveSendWindow()

                self.stopDownloading()

                print('Finalized downloading file')
            else:
                Logger.LogError(
                    "The transaction could not be completed because \
                    the client has not enough space in his disk")

        except FileNotFoundError:
            fileNotExistPacketTimeout = 0
            fileNotExistPacketACKed = False
            fileNotExistPacketSentTime = time.time()
            self.sendFileNotExistPacket()

            while (
                    not fileNotExistPacketACKed) and (
                    fileNotExistPacketTimeout < CLIENT_SOCKET_TIMEOUTS):
                try:
                    self.socket.settimeout(TIMEOUT)
                    nseq = self.receiveACK()
                    if nseq == 0:
                        fileNotExistPacketTimeout = 0
                        fileNotExistPacketACKed = True
                except TimeoutError:
                    fileNotExistPacketTimeout += 1
                    Logger.LogWarning(
                        f"There has been a timeout (timeout \
                        number: {fileNotExistPacketTimeout})")

                if (not fileNotExistPacketACKed) and \
                        (time.time() -
                         fileNotExistPacketSentTime
                         >
                         SELECTIVE_REPEAT_PKT_TOUT):
                    self.sendFileNotExistPacket()
                    fileNotExistPacketSentTime = time.time()

    def sendDownloadRequestResponse(self, file):
        opcode = bytes([DOWNLOAD_REQUEST_RESPONSE_OPCODE])
        zeroedChecksum = (0).to_bytes(4, BYTEORDER)
        nseq = (0).to_bytes(4, BYTEORDER)
        finalChecksum = Checksum.get_checksum(zeroedChecksum
                                              + opcode + nseq,
                                              len(opcode +
                                                  zeroedChecksum +
                                                  nseq),
                                              'sendDownloadRequestResponse')

        header = (opcode, finalChecksum, nseq)

        md5 = hashlib.md5(file).digest()
        filesize = len(file).to_bytes(16, BYTEORDER)

        payload = (md5, filesize)

        message = Packet.pack_download_response(header, payload)

        Logger.LogDebug(
            f"Im sending a packet with opcode: \
            {Utils.bytesToInt(opcode)} and \
            nseq: {Utils.bytesToInt(nseq)}")
        self.send(message)

        nextPacketIsAnOk = False

        Logger.LogDebug("Im waiting for the ack")
        receivedOpcode = self.receiveResponseACK()

        receivedErrorCode = False

        while not nextPacketIsAnOk or receivedErrorCode:
            if receivedOpcode == \
                    DOWNLOAD_REQUEST_OPCODE:  # Client re-sent request
                self.send(message)
                receivedOpcode = self.receiveResponseACK()
            elif receivedOpcode == NO_DISK_SPACE_OPCODE:
                receivedErrorCode = True
            else:
                nextPacketIsAnOk = True

        return receivedErrorCode

    def receiveResponseACK(self):
        received_message, (serverAddres,
                           serverPort) = self.socket.receive(ACK_SIZE)

        header = Packet.unpack_ack(received_message)
        Logger.LogInfo(f"RECEIVED ACK. \t{header}")
        opcode = header['opcode'].to_bytes(1, BYTEORDER)
        checksum = (header['checksum']).to_bytes(4, BYTEORDER)
        nseqToBytes = header['nseq'].to_bytes(4, BYTEORDER)

        if Checksum.is_checksum_valid(
                checksum + opcode + nseqToBytes,
                len(opcode + checksum + nseqToBytes)):
            return header['opcode']
        else:
            Logger.LogWarning("Invalid checksum for ACK receeived")
            return (header['opcode'] + 1)

    def receivePackage(self):
        received_message, (serverAddres, serverPort) = self.socket.receive(
            PACKET_SIZE)

        if Utils.bytesToInt(received_message[:1]) == 0:
            header, payload = Packet.unpack_upload_request(received_message)
        else:
            header, payload = Packet.unpack_package(received_message)

        return header, payload

    def sendACK(self, nseq):
        opcode = bytes([ACK_OPCODE])
        zeroedChecksum = (0).to_bytes(4, BYTEORDER)
        nseqToBytes = nseq.to_bytes(4, BYTEORDER)
        finalChecksum = Checksum.get_checksum(
            zeroedChecksum + opcode + nseqToBytes, len(
                opcode + zeroedChecksum + nseqToBytes), 'sendACK')
        header = (opcode, finalChecksum, nseqToBytes)
        message = Packet.pack_ack(header)
        Logger.LogInfo(f"Sending ACK {nseq} ")
        self.send(message)

    def moveReceiveWindow(self):
        while self.window[0]['isACKSent']:
            lastNseq = self.window[-1]['nseq']
            self.window.pop(0)
            self.window.append({'nseq': lastNseq + 1, 'isACKSent': False})

    def showFile(self, file):
        content = b''
        fileArray = []
        for i in range(len(file)):
            fileArray.append(file[i])

        for e in fileArray:
            content += e

        Logger.LogInfo('######################')
        Logger.LogInfo('El archivo se ha subido al servidor! ')
        Logger.LogInfo('######################')

    def saveFile(self, file, fileName):
        completeName = os.path.join(self.storage, fileName)
        os.makedirs(os.path.dirname(completeName), exist_ok=True)

        fileWriter = open(completeName, "wb")
        for i in range(0, len(file)):
            fileWriter.write(file[i])

        Logger.LogInfo(f"File written into: {completeName}")
        fileWriter.close()

    def isChecksumOK(self, header, payload):
        opcode = header['opcode'].to_bytes(1, BYTEORDER)
        checksum = (header['checksum']).to_bytes(4, BYTEORDER)
        nseqToBytes = header['nseq'].to_bytes(4, BYTEORDER)

        return Checksum.is_checksum_valid(
            checksum + opcode + nseqToBytes,
            len(opcode + checksum + nseqToBytes))

    def stopFileTransfer(self, nseq, fileName, originalMd5, totalPackets):
        opcode = bytes([STOP_FILE_TRANSFER_OPCODE])
        zeroedChecksum = (0).to_bytes(4, BYTEORDER)
        nseqToBytes = nseq.to_bytes(4, BYTEORDER)
        finalChecksum = Checksum.get_checksum(
            zeroedChecksum + opcode + nseqToBytes, len(
                opcode + zeroedChecksum + nseqToBytes), 'sendACK')
        header = (opcode, finalChecksum, nseqToBytes)

        file: bytes
        completeName = os.path.join(self.storage, fileName)
        with open(completeName, 'rb') as file:
            file = file.read()

        md5 = hashlib.md5(file)
        Logger.LogDebug(f"File server MD5: \t{md5.hexdigest()}")
        Logger.LogDebug(f"Client's MD5: \t\t{originalMd5.hex()}")

        state = bytes([STATE_ERROR])  # Not okay by default
        if md5.hexdigest() == originalMd5.hex():
            state = bytes([STATE_OK])

        payload = (md5.digest(), state)
        message = Packet.pack_stop_file_transfer(header, payload)

        Logger.LogInfo("Sending stop file transfer message")
        self.send(message)
        Logger.LogWarning(f"Sending this: {header} and this {payload}")

        stopFileTransferMsgSentAt = time.time()

        communicationFinished = False
        stopCommunicationSocketTimeout = 0

        while (
                not communicationFinished) and (
                stopCommunicationSocketTimeout < LAST_ACK_PACKET_TIMEOUT):
            try:
                self.socket.settimeout(TIMEOUT)
                received_message, (serverAddres,
                                   serverPort) = self.socket.receive(PACKET_SIZE)
                if Utils.bytesToInt(
                    received_message[:1]) == FINAL_ACK_OPCODE:
                    header = Packet.unpack_ack(received_message)
                    finalAckNseq = totalPackets + 1
                    if header['nseq'] == finalAckNseq:
                        stopCommunicationSocketTimeout = 0
                        communicationFinished = True
                else:
                    header, payload = Packet.unpack_package(received_message)
                    self.sendACK(header['nseq'])
                
            except TimeoutError:
                # Acá se da por sentado que el cliente se cerró
                stopCommunicationSocketTimeout += 1

            if (not communicationFinished) and (time.time() -
                                                stopFileTransferMsgSentAt
                                                >
                                                SELECTIVE_REPEAT_PKT_TOUT
                                                ):
                Logger.LogInfo("Re-Sending stop file transfer message")
                self.send(message)
                stopFileTransferMsgSentAt = time.time()

    def stopDownloading(self):
        communicationFinished = False
        stopCommunicationSocketTimeout = 0

        while (
                not communicationFinished) and (
                stopCommunicationSocketTimeout < LAST_ACK_PACKET_TIMEOUT):
            try:
                self.socket.settimeout(TIMEOUT)
                received_message, (serverAddres, serverPort) \
                    = self.socket.receive(STOP_FILE_TRANSFER_SIZE)
                stopCommunicationSocketTimeout = 0
                communicationFinished = True
            except TimeoutError:
                # Acá se da por sentado que el cliente se cerró
                stopCommunicationSocketTimeout += 1

        # CHEQUEAR MD5 QUE SEAN IGUALES

    def sendPackage(self, payload, nseq):
        opcode = bytes([0x4])
        zeroedChecksum = (0).to_bytes(4, BYTEORDER)
        nseqToBytes = (nseq).to_bytes(4, BYTEORDER)

        # Checksum has to go first, for alignment and calculation
        finalChecksum = Checksum.get_checksum(
            zeroedChecksum + opcode + nseqToBytes, len(
                opcode + zeroedChecksum + nseqToBytes), 'sendPackage')

        header = (opcode, finalChecksum, nseqToBytes)
        message = Packet.pack_package(header, payload)
        Logger.LogInfo(f"About to send packet nseq: {nseq}")
        self.send(message)

    def moveSendWindow(self):
        while len(self.window) != 0 and self.window[0]['isACKed']:
            self.window.pop(0)

    def receiveACK(self):
        received_message, (serverAddres,
                           serverPort) = self.socket.receive(ACK_SIZE)

        header = Packet.unpack_ack(received_message)
        Logger.LogInfo(f"RECEIVED ACK. \t{header}")
        opcode = header['opcode'].to_bytes(1, BYTEORDER)
        checksum = (header['checksum']).to_bytes(4, BYTEORDER)
        nseqToBytes = header['nseq'].to_bytes(4, BYTEORDER)

        if Checksum.is_checksum_valid(
                checksum + opcode + nseqToBytes,
                len(opcode + checksum + nseqToBytes)):
            return header['nseq']
        else:
            Logger.LogWarning("Invalid checksum for ACK receeived")
            return header['nseq']

    def sendFileNotExistPacket(self):
        opcode = bytes([FILE_DOES_NOT_EXIST_OPCODE])
        zeroedChecksum = (0).to_bytes(4, BYTEORDER)
        nseqToBytes = (0).to_bytes(4, BYTEORDER)
        finalChecksum = Checksum.get_checksum(
            zeroedChecksum + opcode + nseqToBytes, len(
                opcode + zeroedChecksum + nseqToBytes), 'sendACK')
        header = (opcode, finalChecksum, nseqToBytes)

        message = Packet.pack_ack(header)
        Logger.LogInfo("Sending file does \
                       not exist error.")

        self.send(message)

    def sendNoDiskSpaceErrorPacket(self):
        opcode = bytes([NO_DISK_SPACE_OPCODE])
        zeroedChecksum = (0).to_bytes(4, BYTEORDER)
        nseqToBytes = (0).to_bytes(4, BYTEORDER)
        finalChecksum = Checksum.get_checksum(
            zeroedChecksum + opcode + nseqToBytes, len(
                opcode + zeroedChecksum + nseqToBytes), 'sendACK')
        header = (opcode, finalChecksum, nseqToBytes)

        message = Packet.pack_ack(header)
        Logger.LogInfo("Sending not enough \
                       space error.")

        self.send(message)

    def closeSocket(self):
        self.socket.close()
