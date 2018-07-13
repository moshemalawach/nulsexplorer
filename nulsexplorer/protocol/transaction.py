import struct
from nulsexplorer.protocol.data import (BaseNulsData, NulsDigestData,
                                        write_with_length, read_by_length,
                                        writeUint48, readUint48, hash_twice,
                                        PLACE_HOLDER, ADDRESS_LENGTH, HASH_LENGTH)

class Coin(BaseNulsData):
    def __init__(self, data=None):
        self.owner = None
        self.na = None
        self.lockTime = None
        if data is not None:
            self.parse(data)

    def parse(self, buffer, cursor=0):
        self.owner = read_by_length(buffer, cursor)
        cursor += len(self.owner) + 1
        self.na = struct.unpack("Q", buffer[cursor:cursor+8])[0]
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
        self.module_data = dict()
        if data is not None:
            self.parse(data)

    def _parse_data(self, buffer, cursor=0):
        md = self.module_data
        if self.type == 1: # consensus reward
            cursor += len(PLACE_HOLDER)

        elif self.type == 2: # tranfer
            cursor += len(PLACE_HOLDER)

        elif self.type == 3: # alias
            md['address'] = read_by_length(buffer, cursor)
            cursor += len(md['address']) + 1

            md['alias'] = read_by_length(buffer, cursor)
            cursor += len(md['alias']) + 1
            md['alias'] = md['alias'].decode('utf-8')

        elif self.type == 4: # register agent
            md['deposit'] = struct.unpack("Q", buffer[cursor:cursor+8])[0]
            cursor += 8
            md['agentAddress'] = buffer[cursor:cursor+ADDRESS_LENGTH]
            cursor += ADDRESS_LENGTH
            md['packingAddress'] = buffer[cursor:cursor+ADDRESS_LENGTH]
            cursor += ADDRESS_LENGTH
            md['rewardAddress'] = buffer[cursor:cursor+ADDRESS_LENGTH]
            cursor += ADDRESS_LENGTH
            md['commissionRate'] = struct.unpack("d", buffer[cursor:cursor+8])[0]
            cursor += 8
            return cursor

        elif self.type == 5: # join consensus
            md['deposit'] = struct.unpack("Q", buffer[cursor:cursor+8])[0]
            cursor += 8
            md['address'] = buffer[cursor:cursor+ADDRESS_LENGTH]
            cursor += ADDRESS_LENGTH
            md['agentHash'] = buffer[cursor:cursor+HASH_LENGTH]
            cursor += HASH_LENGTH

        elif self.type == 6: # cancel deposit
            md['joinTxHash'] = buffer[cursor:cursor+HASH_LENGTH]
            cursor += HASH_LENGTH

        elif self.type == 7: # yellow card
            md['count'] = buffer[cursor]
            cursor += 1
            addresses = list()
            for i in range(md['count']):
                addresses.append(buffer[cursor:cursor+ADDRESS_LENGTH])
                cursor += ADDRESS_LENGTH
            md['addresses'] = addresses

        elif self.type == 8: # red card
            md['address'] = read_by_length(buffer, cursor)
            cursor += len(md['address']) + 1
            md['reason'] = buffer[cursor]
            cursor += 1
            md['evidence'] = read_by_length(buffer, cursor)
            cursor += len(md['evidence']) + 1

        elif self.type == 9: # stop agent
            md['createTxHash'] = buffer[cursor:cursor+HASH_LENGTH]
            cursor += HASH_LENGTH

        return cursor

    def parse(self, buffer, cursor=0):
        self.type = struct.unpack("H", buffer[cursor:cursor+2])[0]
        cursor += 2
        self.time = readUint48(buffer, cursor)
        cursor += 6
        self.remark = read_by_length(buffer, cursor)
        cursor += len(self.remark) + 1

        cursor = self._parse_data(buffer, cursor)

        self.coin_data = CoinData()
        cursor = self.coin_data.parse(buffer, cursor)

        #self.hash_bytes = hash_twice(self.serialize())
        #self.hash = NulsDigestData(data=self.hash_bytes, alg_type=0)

        self.scriptSig = read_by_length(buffer, cursor)
        cursor += len(self.scriptSig) + 1

        return cursor

    #def size(self):
    #    return 0
