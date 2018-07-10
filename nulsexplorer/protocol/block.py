import struct
from nulsexplorer.protocol.data import (BaseNulsData, NulsDigestData,
                                        write_with_length, read_by_length,
                                        writeUint48, readUint48, hash_twice)

class P2PKHScriptSig(BaseNulsData):
    DEFAULT_SERIALIZE_LENGTH = 110

    def __init__(self, data=None):
        self.public_key = None

        if data is not None:
            self.parse(data)

    def parse(self, buffer, cursor=0):
        self.public_key = read_by_length(buffer, cursor=cursor)
        cursor += len(self.public_key) + 1
        self.sign_alg_type = buffer[cursor]
        cursor += 1
        self.sign_bytes = read_by_length(buffer, cursor=cursor)
        cursor += 1

    @property
    def size(self):
        nsize = len(self.public_key) + len(self.sign_bytes) + 3
        print (nsize, self.DEFAULT_SERIALIZE_LENGTH)
        return nsize

    def serialize(self):
        return write_with_length(self.public_key) + bytes([self.sign_alg_type ])\
               + write_with_length(self.sign_bytes)

class BlockHeader(BaseNulsData):
    def __init__(self, data=None):
        self.preHash = None
        self.merkleHash = None
        self.time = None
        self.height = None
        self.txCount = None
        self.extend = None
        self.scriptSig = None
        self.raw_data = None

        if data is not None:
            self.parse(data)

    def parse(self, buffer):
        cursor = 0
        self.preHash = NulsDigestData(data=buffer)
        cursor += self.preHash.size
        self.merkleHash = NulsDigestData(data=buffer[cursor:])
        cursor += self.merkleHash.size
        self.time = readUint48(buffer, cursor)
        cursor += 6
        self.height, self.txCount = struct.unpack("II", buffer[cursor:cursor+8])
        cursor += 8

        self.extend = read_by_length(buffer, cursor)
        print(len(self.extend), self.extend.hex())
        cursor += len(self.extend) + 1

        self.hash_bytes = hash_twice(self.serialize())
        self.hash = NulsDigestData(data=self.hash_bytes, alg_type=0)

        self.scriptSig = P2PKHScriptSig(data=buffer[cursor:])
        cursor += self.scriptSig.size

        self.raw_data = buffer[:cursor]

    def serialize(self):
        out = bytes()
        out += self._prepare(self.preHash)
        out += self._prepare(self.merkleHash)
        out += writeUint48(self.time)
        out += struct.pack("II", self.height, self.txCount)
        out += write_with_length(self.extend)
        out += self._prepare(self.scriptSig)
        return out


    def __str__(self):
        return  "%s%s" % (
            self.preHash,
            self.merkleHash
        )

class Block(BaseNulsData):
    def __init__(self, data=None):
        self.header = None

        if data is not None:
            self.parse(data)

    def parse(self, buffer):
        self.size = len(buffer)
        self.header = BlockHeader(buffer)

    def __str__(self):
        return  "%s" % (
            self.header
        )

    def serialize(self):
        return

def read_block_header(bytes):
    pass

if __name__ == "__main__":
    import base64
    v = b'ACCAI2bW5L0nf8oQriPGi/YrItgV3xglKYlYmBqHv9jlbgAglHk5VUr605JRswl/3osRlWzWZAAzwg6K7Wqh7eKh0UIAeuWAZAHO1QAAAgAAAA5SVggAFgCgHuKAZAEWACED+t+fCvlmYmJvoJYIlBlkX6/MjUpf7eVz8H+1I4yP2a0ARjBEAiBtkeqYlC7djU+HhZuoRZbzkmVpC6MOSh3douGlEPY0vwIgeTq8klF+cH8kRj+VWsVRjglS2GAfaED/ZxnyUapDVuMBAAB65YBkAQD/////AAEXAQAB3X5dBTFUIjmFGy/M+Bp/fFp6k9P8jOEKAAAAALbZAAAAAAAHAAB65YBkAQABAQABd8BiHOOpmAoKXAS4+8tipgjjt/3/////AA=='
    print(base64.b64decode(v).hex())
    block = Block(base64.b64decode(v))
    print (block.header.preHash,
           block.header.merkleHash,
           block.header.hash)
    print (block.header.time,
           block.header.height,
           block.header.txCount)
