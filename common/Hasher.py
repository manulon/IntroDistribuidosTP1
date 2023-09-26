import hashlib
class Hasher:

    def checksum(self, stream):
        return sum(stream)
    
    def md5(self, file):
        return hashlib.md5(file).hexdigest()
        #retorna -> '2a53375ff139d9837e93a38a279d63e5'