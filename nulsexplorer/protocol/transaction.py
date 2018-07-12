import struct
from nulsexplorer.protocol.data import (BaseNulsData, NulsDigestData,
                                        write_with_length, read_by_length,
                                        writeUint48, readUint48, hash_twice)

class Coin(BaseNulsData):
    def __init__(self, data=None):
        self.owner = None
        self.na = None
        self.lockTime = None
        if data is not None:
            self.parse(data)

    def parse(self, buffer, cursor=0):
        self.owner = read_by_length(buffer, cursor)
        print(self.owner.hex())
        cursor += len(self.owner) + 1
        print('c', len(buffer), cursor)
        self.na = struct.unpack("Q", buffer[cursor:cursor+8])
        cursor += 8
        self.lockTime = readUint48(buffer, cursor)
        cursor += 6
        return cursor

class CoinData(BaseNulsData):
    def __init__(self, data=None):
        self.from_count = None
        self.to_count = None
        self.inputs = None
        self.outputs = None

        if data is not None:
            self.parse(data)

    def parse(self, buffer, cursor=0):
        print('cd', len(buffer), cursor)
        self.from_count = buffer[cursor]
        cursor += 1
        self.inputs = list()
        for i in range(self.from_count):
            coin = Coin()
            cursor = coin.parse(buffer, cursor)
            self.inputs.append(coin)

        self.to_count = buffer[cursor]
        cursor += 1
        self.outputs = list()
        for i in range(self.to_count):
            coin = Coin()
            cursor = coin.parse(buffer, cursor)
            self.outputs.append(coin)

        return cursor

class Transaction(BaseNulsData):
    def __init__(self, data=None):
        self.type = None
        self.time = None
        self.scriptSig = None
        if data is not None:
            self.parse(data)

    def parse_data(self, buffer, cursor=0):
        if self.type == 1: # consensus reward
            pass

        elif self.type == 3: # alias
            pass

    def parse(self, buffer, cursor=0):
        self.type = struct.unpack("H", buffer[cursor:cursor+2])
        cursor += 2
        self.time = readUint48(buffer, cursor)
        cursor += 6
        self.remark = read_by_length(buffer, cursor)
        cursor += len(self.remark) + 1

        self.coin_data = CoinData()
        cursor = self.coin_data.parse(buffer, cursor)

        #self.hash_bytes = hash_twice(self.serialize())
        #self.hash = NulsDigestData(data=self.hash_bytes, alg_type=0)

        self.scriptSig = read_by_length(buffer, cursor)
        cursor += len(self.scriptSig) + 1

        return cursor

    #def size(self):
    #    return 0
