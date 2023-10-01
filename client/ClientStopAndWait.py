import hashlib
import math
from common.Checksum import Checksum
from common.Logger import Logger
from common.Packet import Packet
import common.constants as const


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

    def upload(self, filename):
        Logger.LogInfo(f"About to start uploading: {filename}")

        file: bytes
        with open(filename, 'rb') as file:
            file = file.read()

        md5 = hashlib.md5(file)
        filesize = len(file)

        self.sendUploadRequest(filename, filesize, md5.digest())
        chunksize = self.receiveFileTransferTypeResponse()
        if chunksize == const.ERROR_CODE:
            return

        totalPackets = math.ceil(filesize / chunksize)
        Logger.LogInfo(
            f"File: {filename} - Size: {filesize} - md5: {md5.hexdigest()} - Packets to send: {totalPackets}")
        self.sendFile(file, chunksize)

    def sendUploadRequest(self, fileName, fileSize, md5):
        opcode = bytes([const.UPLOAD_REQUEST_OPCODE])
        zeroedChecksum = (0).to_bytes(4, const.BYTEORDER)
        nseq = (0).to_bytes(1, const.BYTEORDER)
        finalChecksum = Checksum.get_checksum(
            zeroedChecksum + opcode + nseq, len(opcode + zeroedChecksum + nseq), 'sendUploadRequest')
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
        received_message, _ = self.socket.receive(
            const.FILE_TRANSFER_TYPE_RESPONSE_SIZE)
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
            elif opcode == const.FILE_ALREADY_EXISTS_OPCODE:
                Logger.LogError(
                    'The file that you are trying to upload already exists in the server')
            else:
                Logger.LogError('Uknown error, retry')
            return const.ERROR_CODE

        '''
        header, payload = Packet.unpack_file_transfer_type_response(received_message)
        print('----------')
        print('Recibi este header:', header)
        print('El tamaño del chunk es:', payload)
        print('¡Adios!')
        '''

    def sendFile(self, file, chunksize):
        fileSize = len(file)
        totalPackets = fileSize / chunksize
        packetsPushed = 0

        while (packetsPushed < totalPackets):
            sequenceNumber = (packetsPushed + 1) % 2  # starts in 1
            payload = file[packetsPushed *
                           chunksize: (packetsPushed + 1) * chunksize]
            self.sendPacket(sequenceNumber, payload)
            ackNseq = self.receiveACK()
            if (ackNseq == sequenceNumber):
                packetsPushed += 1
            else:
                while(ackNseq != sequenceNumber):  # case 4
                    self.sendPacket(sequenceNumber, payload)
                    ackNseq = self.receiveACK()

        self.stopUploading(int(totalPackets + 1))

        print('File transfer has ended.')
        # Logger.LogInfo(f"Total packets to send: {totalPackets}, nseq: {nseq}, socket timeouts: {socketTimeouts}")

    def sendPacket(self, nseq, payload):
        opcode = bytes([const.PACKET_OPCODE])
        checksum = (2).to_bytes(4, const.BYTEORDER)
        nseqToBytes = nseq.to_bytes(4, const.BYTEORDER)
        header = (opcode, checksum, nseqToBytes)

        message = Packet.pack_package(header, payload)
        self.send(message)

    def send(self, message):
        self.socket.send(message, self.serverAddress, self.serverPort)

    def receiveACK(self):
        # timeout?
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
                "There's been an error uploading the file in the server. File corrupt in the server")

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

    def download(self, filename):
        self.sendDownloadRequest(filename)
        '''
            Enviar download request con filename
            Esperar respuesta del servidor
            tomar tamano del archivo y chunksize
            Verificar si hay espacio en disco para la descarga
            paquetesTotales = tam/chunksize
            md5 = md5 del server
            enviar OK al servidor
            Mientras ACKs enviados < PaquetesTotales
                esperar a recibir paquete
                if cheksum y nseq OK
                    Mandar Ack del paquete
                    appendear bytes del payload
                    acks enviados ++
                else
                    solo mandar ack pues el servidor hizo una retransmision por perdida
            verificar mda5
            if mda5 bien
                ENVIAR ok final y retornar
        '''

    def sendDownloadRequest(self, fileName):
            opcode = bytes([const.DOWNLOAD_REQUEST_OPCODE])
            zeroedChecksum = (0).to_bytes(4, const.BYTEORDER)
            nseq = (0).to_bytes(1, const.BYTEORDER)
            finalChecksum = Checksum.get_checksum(
                zeroedChecksum + opcode + nseq, len(opcode + zeroedChecksum + nseq), 'sendDownloadRequest')
            header = (opcode, finalChecksum, nseq)

            protocol = self.protocolID
            fileName = fileName.encode()
            payload = (
                protocol,
                fileName)
            message = Packet.pack_package(header, payload)
            self.send(message)