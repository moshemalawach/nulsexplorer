import struct
from nulsexplorer.protocol.data import (BaseNulsData, NulsDigestData,
                                        write_with_length, read_by_length,
                                        writeUint48, readUint48, hash_twice)
from nulsexplorer.protocol.transaction import Transaction

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

    def parse(self, buffer, cursor=0):
        self.preHash = NulsDigestData(data=buffer)
        cursor += self.preHash.size
        self.merkleHash = NulsDigestData(data=buffer[cursor:])
        cursor += self.merkleHash.size
        self.time = readUint48(buffer, cursor)
        cursor += 6
        self.height, self.txCount = struct.unpack("II", buffer[cursor:cursor+8])
        cursor += 8

        self.extend = read_by_length(buffer, cursor)
        cursor += len(self.extend) + 1

        self.hash_bytes = hash_twice(self.serialize())
        self.hash = NulsDigestData(data=self.hash_bytes, alg_type=0)

        self.scriptSig = P2PKHScriptSig(data=buffer[cursor:])
        cursor += self.scriptSig.size

        self.raw_data = buffer[:cursor]
        return cursor

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
        self.transactions = None

        if data is not None:
            self.parse(data)

    def parse(self, buffer):
        self.size = len(buffer)
        self.header = BlockHeader()
        cursor = self.header.parse(buffer)

        self.transactions = list()
        for ntx in range(self.header.txCount):
            tx = Transaction()
            cursor = tx.parse(buffer, cursor)
            self.transactions.append(tx)

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
    #v = b'ACCAI2bW5L0nf8oQriPGi/YrItgV3xglKYlYmBqHv9jlbgAglHk5VUr605JRswl/3osRlWzWZAAzwg6K7Wqh7eKh0UIAeuWAZAHO1QAAAgAAAA5SVggAFgCgHuKAZAEWACED+t+fCvlmYmJvoJYIlBlkX6/MjUpf7eVz8H+1I4yP2a0ARjBEAiBtkeqYlC7djU+HhZuoRZbzkmVpC6MOSh3douGlEPY0vwIgeTq8klF+cH8kRj+VWsVRjglS2GAfaED/ZxnyUapDVuMBAAB65YBkAQD/////AAEXAQAB3X5dBTFUIjmFGy/M+Bp/fFp6k9P8jOEKAAAAALbZAAAAAAAHAAB65YBkAQABAQABd8BiHOOpmAoKXAS4+8tipgjjt/3/////AA=='
    v = b"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"

    print(base64.b64decode(v).hex())
    block = Block(base64.b64decode(v))
    print (block.header.preHash,
           block.header.merkleHash,
           block.header.hash)
    print (block.header.time,
           block.header.height,
           block.header.txCount)
    for tx in block.transactions:
        print("transaction type", tx.type)
        print("remark", tx.remark)
        print("coin data", tx.coin_data.inputs, tx.coin_data.outputs)
