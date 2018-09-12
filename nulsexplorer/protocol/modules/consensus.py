from nulsexplorer.protocol.data import (write_with_length, read_by_length,
                                        writeUint48, readUint48,
                                        writeUint32, writeUint64,
                                        writeVarInt, hash_twice, VarInt,
                                        timestamp_from_time,
                                        address_from_hash,
                                        hash_from_address,
                                        PLACE_HOLDER, ADDRESS_LENGTH, HASH_LENGTH)
from nulsexplorer.protocol.register import register_tx_type
from binascii import hexlify, unhexlify

class RegisterAgentData(BaseModuleData):
    @classmethod
    def from_buffer(cls, buffer, cursor=0):
        md = dict()
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
        return cursor, md

    @classmethod
    def to_buffer(cls, md):
        output = struct.pack("Q", md['deposit'])
        output += hash_from_address(md['agentAddress'])
        output += hash_from_address(md['packingAddress'])
        output += hash_from_address(md['rewardAddress'])
        output += struct.pack("d", md['commissionRate'])
        return output

register_tx_type(4, RegisterAgentData)

class JoinConsensusData(BaseModuleData):
    @classmethod
    def from_buffer(cls, buffer, cursor=0):
        md = dict()
        md['deposit'] = struct.unpack("Q", buffer[cursor:cursor+8])[0]
        cursor += 8
        md['address'] = buffer[cursor:cursor+ADDRESS_LENGTH]
        cursor += ADDRESS_LENGTH
        md['address'] = address_from_hash(md['address'])
        md['agentHash'] = buffer[cursor:cursor+HASH_LENGTH].hex()
        cursor += HASH_LENGTH
        return cursor, md

    @classmethod
    def to_buffer(cls, md):
        output = struct.pack("Q", md['deposit'])
        output += hash_from_address(md['address'])
        output += unhexlify(md['agentHash'])
        return output

register_tx_type(5, JoinConsensusData)

class CancelDepositData(BaseModuleData):
    @classmethod
    def from_buffer(cls, buffer, cursor=0):
        md = dict()
        md['joinTxHash'] = buffer[cursor:cursor+HASH_LENGTH].hex()
        cursor += HASH_LENGTH
        return cursor, md

    @classmethod
    def to_buffer(cls, md):
        output = unhexlify(md['joinTxHash'])
        return output

register_tx_type(6, CancelDepositData)

class YellowCardData(BaseModuleData):
    @classmethod
    def from_buffer(cls, buffer, cursor=0):
        md = dict()
        md['count'] = buffer[cursor]
        cursor += 1
        addresses = list()
        for i in range(md['count']):
            addresses.append(buffer[cursor:cursor+ADDRESS_LENGTH])
            cursor += ADDRESS_LENGTH
        md['addresses'] = list(map(address_from_hash, addresses))
        return cursor, md

    @classmethod
    def to_buffer(cls, md):
        output = VarInt(md['count']).encode()
        for address in md['addresses']:
            output += hash_from_address(address)
        return output

register_tx_type(7, YellowCardData)


class RedCardData(BaseModuleData):
    @classmethod
    def from_buffer(cls, buffer, cursor=0):
        md = dict()
        pos, md['address'] = read_by_length(buffer, cursor)
        cursor += pos
        md['address'] = address_from_hash(md['address'])
        md['reason'] = buffer[cursor]
        cursor += 1
        pos, md['evidence'] = read_by_length(buffer, cursor)
        cursor += pos
        md['evidence'] = md['evidence'].hex()
        return cursor, md

    @classmethod
    def to_buffer(cls, md):
        output = write_with_length(hash_from_address(md['address']))
        output += VarInt(md['reason']).encode()
        output += write_with_length(unhexlify(md['evidence']))
        return output

register_tx_type(8, RedCardData)


class StopAgentData(BaseModuleData):
    @classmethod
    def from_buffer(cls, buffer, cursor=0):
        md = dict()
        md['createTxHash'] = buffer[cursor:cursor+HASH_LENGTH].hex()
        cursor += HASH_LENGTH
        return cursor, md

    @classmethod
    def to_buffer(cls, md):
        output = unhexlify(md['createTxHash'])
        return output

register_tx_type(9, StopAgentData)
