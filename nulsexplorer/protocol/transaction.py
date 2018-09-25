import struct
import base64
from binascii import hexlify, unhexlify
from datetime import datetime
from nulsexplorer.protocol.data import (BaseNulsData, NulsDigestData,
                                        NulsSignature,
                                        write_with_length, read_by_length,
                                        writeUint48, readUint48,
                                        writeUint32, writeUint64,
                                        writeVarInt, hash_twice, VarInt,
                                        timestamp_from_time,
                                        address_from_hash,
                                        hash_from_address,
                                        PLACE_HOLDER, ADDRESS_LENGTH, HASH_LENGTH)
from nulsexplorer.modules.register import TX_TYPES_REGISTER, process_tx

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
                fc = VarInt()
                fc.parse(owner, HASH_LENGTH)
                self.fromIndex = fc.value
                assert fc.originallyEncodedSize == val
            else:
                self.fromIndex = owner[-1]
            self.fromHash = owner[:HASH_LENGTH]
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
            val['addressHash'] = self.address

        if self.fromHash is not None:
            val['fromHash'] = self.fromHash.hex()
            val['fromIndex'] = self.fromIndex

        return val

    @classmethod
    def from_dict(cls, value):
        item = cls()
        item.address = value.get('address', None)
        item.fromHash = value.get('fromHash', None)
        if item.fromHash is not None:
            item.fromHash = unhexlify(item.fromHash)
        item.fromIndex = value.get('fromIndex', None)
        item.lockTime = value.get('lockTime', 0)
        item.na = value.get('value', None)

        return item

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

        #if data is not None:
        #    self.parse(data)

    async def parse(self, buffer, cursor=0):
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

    async def serialize(self):
        output = b""
        output += VarInt(len(self.inputs)).encode()
        for coin in self.inputs:
            output += coin.serialize()
        output += VarInt(len(self.outputs)).encode()
        for coin in self.outputs:
            output += coin.serialize()

        return output

class Transaction(BaseNulsData):
    def __init__(self, height=None, hash_varint=False):
        self.type = None
        self.time = None
        self.hash = None
        self.height = height
        self.scriptSig = None
        self.module_data = dict()
        self.coin_data = CoinData()
        self.hash_varint = hash_varint

    async def _parse_data(self, buffer, cursor=0):

        if self.type in TX_TYPES_REGISTER:
            cursor, self.module_data = await TX_TYPES_REGISTER[self.type].from_buffer(
                buffer, cursor)
        else:
            cursor += len(PLACE_HOLDER)

        return cursor

    async def _write_data(self):
        output = b""
        if self.type in TX_TYPES_REGISTER:
            output += await TX_TYPES_REGISTER[self.type].to_buffer(self.module_data)
        else:
            output += PLACE_HOLDER

        return output

    def get_hash(self):
        if self.hash_varint:
            values = bytes((self.type,)) \
                    + bytes((255,)) + writeUint64(self.time)
        else:
            values = struct.pack("H", self.type) \
                    + writeUint48(self.time)

        values += write_with_length(self.remark) \
                + self._write_data() \
                + self.coin_data.serialize()

        hash_bytes = hash_twice(values)
        hash = NulsDigestData(data=hash_bytes, alg_type=0)
        return hash

    async def parse(self, buffer, cursor=0):
        st_cursor = cursor
        self.type = struct.unpack("H", buffer[cursor:cursor+2])[0]
        cursor += 2
        self.time = readUint48(buffer, cursor)
        cursor += 6


        st2_cursor = cursor

        pos, self.remark = read_by_length(buffer, cursor, check_size=True)
        cursor += pos

        cursor = await self._parse_data(buffer, cursor)

        self.coin_data = CoinData()
        cursor = await self.coin_data.parse(buffer, cursor)
        med_cursor = cursor

        if self.hash_varint:
            values = bytes((self.type,)) \
                    + bytes((255,)) + writeUint64(self.time)
        else:
            values = struct.pack("H", self.type) \
                    + writeUint48(self.time)

        values += buffer[st2_cursor:med_cursor]

        self.hash_bytes = hash_twice(values)
        self.hash = NulsDigestData(data=self.hash_bytes, alg_type=0)

        pos, self.scriptSig = read_by_length(buffer, cursor, check_size=True)
        cursor += pos
        end_cursor = cursor
        self.size = end_cursor - st_cursor

        return cursor


    async def to_dict(self):
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

    @classmethod
    async def from_dict(cls, value):
        item = cls()
        #item.hash = value.get('hash', '').encode('UTF-8')
        item.type = value['type']
        item.time = value.get('time')
        if item.time is None:
            item.time = timestamp_from_time(datetime.now())
        item.height = value.get('blockHeight') # optionnal, when creating a tx.
        item.remark = value.get('remark', b'')
        item.scriptSig = value.get('scriptSig')
        item.size = value.get('size')
        item.module_data = value.get('info') # this should be fixed.

        for input in value.get('inputs'):
            item.coin_data.inputs.append(Coin.from_dict(input))
        item.coin_data.from_count = len(item.coin_data.inputs)

        for output in value.get('outputs'):
            item.coin_data.outputs.append(Coin.from_dict(output))
        item.coin_data.to_count = len(item.coin_data.outputs)

        return item

    async def sign_tx(self, pri_key):
        self.signature = NulsSignature.sign_data(pri_key,
                                                 self.get_hash().digest_bytes)
        self.scriptSig = self.signature.serialize()

    async def serialize(self):
        output = b""
        output += struct.pack("H", self.type)
        output += writeUint48(self.time)
        output += write_with_length(self.remark)
        output += await self._write_data()
        output += await self.coin_data.serialize()
        output += self.scriptSig is not None and write_with_length(self.scriptSig) or PLACE_HOLDER
        return output

    async def run_processor(self):
        return await process_tx(self, step="pre")
