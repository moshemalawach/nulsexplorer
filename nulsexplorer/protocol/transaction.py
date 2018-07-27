import struct
import base64
from binascii import hexlify, unhexlify
from nulsexplorer.protocol.data import (BaseNulsData, NulsDigestData,
                                        write_with_length, read_by_length,
                                        writeUint48, readUint48,
                                        writeUint32, writeUint64,
                                        writeVarInt, hash_twice, VarInt,
                                        address_from_hash,
                                        hash_from_address,
                                        PLACE_HOLDER, ADDRESS_LENGTH, HASH_LENGTH)

class Coin(BaseNulsData):
    def __init__(self, data=None):
        self.address = None
        self.fromHash = None
        self.fromIndex = None
        self.na = None
        self.lockTime = None

        if data is not None:
            self.parse(data)

    def parse(self, buffer, cursor=0):
        pos, owner = read_by_length(buffer, cursor)
        cursor += pos

        if len(owner) > ADDRESS_LENGTH:
            val = (len(owner) - HASH_LENGTH)
            if (val > 1):
                raise ValueError("Long int for index found")
            self.fromHash = owner[:HASH_LENGTH-len(owner)]
            self.fromIndex = owner[-1]
        else:
            self.address = owner

        self.na = struct.unpack("Q", buffer[cursor:cursor+8])[0]
        cursor += 8
        self.lockTime = readUint48(buffer, cursor)
        cursor += 6
        return cursor

    def to_dict(self):
        val = {
            'value': self.na,
            'lockTime': self.lockTime
        }
        if self.address is not None:
            val['address'] = address_from_hash(self.address)

        if self.fromHash is not None:
            val['fromHash'] = self.fromHash.hex()
            val['fromIndex'] = self.fromIndex

        return val

    def __repr__(self):
        return "<UTXO Coin: {}: {} - {}>".format((self.address or self.fromHash).hex(), self.na, self.lockTime)

    def serialize(self):
        output = b""
        if self.fromHash is not None:
            output += write_with_length(self.fromHash + bytes([self.fromIndex]))
        elif self.address is not None:
            output += write_with_length(self.address)
        else:
            raise ValueError("Either fromHash and fromId should be set or address.")

        output += struct.pack("Q", self.na)
        output += writeUint48(self.lockTime)
        return output

class CoinData(BaseNulsData):
    def __init__(self, data=None):
        self.from_count = None
        self.to_count = None
        self.inputs = list()
        self.outputs = list()

        if data is not None:
            self.parse(data)

    def parse(self, buffer, cursor=0):
        if buffer[cursor:cursor+4] == PLACE_HOLDER:
            return cursor+4

        fc = VarInt()
        fc.parse(buffer, cursor)
        self.from_count = fc.value
        cursor += fc.originallyEncodedSize
        self.inputs = list()
        for i in range(self.from_count):
            coin = Coin()
            cursor = coin.parse(buffer, cursor)
            self.inputs.append(coin)

        tc = VarInt()
        tc.parse(buffer, cursor)
        self.to_count = tc.value
        cursor += tc.originallyEncodedSize
        #self.to_count = buffer[cursor]
        self.outputs = list()
        for i in range(self.to_count):
            coin = Coin()
            cursor = coin.parse(buffer, cursor)
            self.outputs.append(coin)

        return cursor

    def get_fee(self):
        return sum([i.na for i in self.inputs]) - sum([o.na for o in self.outputs])

    def get_output_sum(self):
        return sum([o.na for o in self.outputs])

    def serialize(self):
        output = b""
        output += VarInt(self.from_count).encode()
        for coin in self.inputs:
            output += coin.serialize()
        output += VarInt(self.to_count).encode()
        for coin in self.outputs:
            output += coin.serialize()

        return output

class Transaction(BaseNulsData):
    def __init__(self, data=None, height=None):
        self.type = None
        self.time = None
        self.hash = None
        self.height = height
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
            pos, md['address'] = read_by_length(buffer, cursor)
            cursor += pos

            pos, md['alias'] = read_by_length(buffer, cursor)
            cursor += pos
            md['alias'] = md['alias'].decode('utf-8')

        elif self.type == 4: # register agent
            md['deposit'] = struct.unpack("Q", buffer[cursor:cursor+8])[0]
            cursor += 8
            md['agentAddress'] = buffer[cursor:cursor+ADDRESS_LENGTH]
            cursor += ADDRESS_LENGTH
            md['agentAddress'] = address_from_hash(md['agentAddress'])
            md['packingAddress'] = buffer[cursor:cursor+ADDRESS_LENGTH]
            cursor += ADDRESS_LENGTH
            md['packingAddress'] = address_from_hash(md['packingAddress'])
            md['rewardAddress'] = buffer[cursor:cursor+ADDRESS_LENGTH]
            cursor += ADDRESS_LENGTH
            md['rewardAddress'] = address_from_hash(md['rewardAddress'])
            md['commissionRate'] = struct.unpack("d", buffer[cursor:cursor+8])[0]
            cursor += 8
            return cursor

        elif self.type == 5: # join consensus
            md['deposit'] = struct.unpack("Q", buffer[cursor:cursor+8])[0]
            cursor += 8
            md['address'] = buffer[cursor:cursor+ADDRESS_LENGTH]
            cursor += ADDRESS_LENGTH
            md['address'] = address_from_hash(md['address'])
            md['agentHash'] = buffer[cursor:cursor+HASH_LENGTH].hex()
            cursor += HASH_LENGTH

        elif self.type == 6: # cancel deposit
            md['joinTxHash'] = buffer[cursor:cursor+HASH_LENGTH].hex()
            cursor += HASH_LENGTH

        elif self.type == 7: # yellow card
            md['count'] = buffer[cursor]
            cursor += 1
            addresses = list()
            for i in range(md['count']):
                addresses.append(buffer[cursor:cursor+ADDRESS_LENGTH])
                cursor += ADDRESS_LENGTH
            md['addresses'] = list(map(address_from_hash, addresses))

        elif self.type == 8: # red card
            pos, md['address'] = read_by_length(buffer, cursor)
            cursor += pos
            md['address'] = address_from_hash(md['address'])
            md['reason'] = buffer[cursor]
            cursor += 1
            pos, md['evidence'] = read_by_length(buffer, cursor)
            cursor += pos
            md['evidence'] = md['evidence'].hex()

        elif self.type == 9: # stop agent
            md['createTxHash'] = buffer[cursor:cursor+HASH_LENGTH].hex()
            cursor += HASH_LENGTH

        return cursor

    def parse(self, buffer, cursor=0):
        st_cursor = cursor
        self.type = struct.unpack("H", buffer[cursor:cursor+2])[0]
        cursor += 2
        self.time = readUint48(buffer, cursor)
        cursor += 6


        st2_cursor = cursor

        pos, self.remark = read_by_length(buffer, cursor, check_size=True)
        cursor += pos

        cursor = self._parse_data(buffer, cursor)

        self.coin_data = CoinData()
        cursor = self.coin_data.parse(buffer, cursor)
        med_cursor = cursor

        values = bytes((self.type,)) \
                + bytes((255,)) + writeUint64(self.time) \
                + buffer[st2_cursor:med_cursor]

        self.hash_bytes = hash_twice(values)
        self.hash = NulsDigestData(data=self.hash_bytes, alg_type=0)

        pos, self.scriptSig = read_by_length(buffer, cursor, check_size=True)
        cursor += pos
        end_cursor = cursor
        self.size = end_cursor - st_cursor

        return cursor


    def to_dict(self):
        try:
            remark = self.remark and self.remark.decode('utf-8') or None
        except UnicodeDecodeError:
            remark = base64.b64encode(self.remark).decode("utf-8")

        return {
            'hash': str(self.hash),
            'type': self.type,
            'time': self.time,
            'blockHeight': self.height,
            'fee': self.type != 1 and self.coin_data.get_fee() or 0,
            'remark': remark,
            'scriptSig': self.scriptSig and self.scriptSig.hex() or None,
            'size': self.size,
            'info': self.module_data,
            'inputs': [utxo.to_dict() for utxo in self.coin_data.inputs],
            'outputs': [utxo.to_dict() for utxo in self.coin_data.outputs]
        }

    def _write_data(self):
        md = self.module_data
        output = b""

        if self.type == 1: # consensus reward
            output += PLACE_HOLDER

        elif self.type == 2: # tranfer
            output += PLACE_HOLDER

        elif self.type == 3: # alias
            output += write_with_length(hash_from_address(md['address']))
            output += write_with_length(md['alias'].encode('utf-8'))

        elif self.type == 4: # register agent
            output += struct.pack("Q", md['deposit'])
            output += hash_from_address(md['agentAddress'])
            output += hash_from_address(md['packingAddress'])
            output += hash_from_address(md['rewardAddress'])
            output += struct.pack("d", md['commissionRate'])

        elif self.type == 5: # join consensus
            output += struct.pack("Q", md['deposit'])
            output += hash_from_address(md['address'])
            output += unhexlify(md['agentHash'])

        elif self.type == 6: # cancel deposit
            output += unhexlify(md['joinTxHash'])

        elif self.type == 7: # yellow card
            output += VarInt(md['count']).encode()
            for address in md['addresses']:
                output += hash_from_address(address)

        elif self.type == 8: # red card
            output += write_with_length(hash_from_address(md['address']))
            output += VarInt(md['reason']).encode()
            output += write_with_length(unhexlify(md['evidence']))

        elif self.type == 9: # stop agent
            output += unhexlify(md['createTxHash'])

        return cursor

    def serialize(self):
        output = b""
        output += struct.pack("H", self.type)
        output += writeUint48(self.time)
        output += write_with_length(self.remark)
        output += self._write_data()
        output += self.coin_data.serialize()
        output += write_with_length(self.scriptSig)
        return output
