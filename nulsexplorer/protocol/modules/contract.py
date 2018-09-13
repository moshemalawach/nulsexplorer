from nulsexplorer.protocol.data import (write_with_length, read_by_length,
                                        hash_from_address, address_from_hash,
                                        VarInt,
                                        parse_varint, write_varint)
from nulsexplorer.protocol.register import register_tx_type
from .base import BaseModuleData

class CreateContractData(BaseModuleData):
    @classmethod
    async def from_buffer(cls, buffer, cursor=0):
        md = dict()
        pos, md['sender'] = read_by_length(buffer, cursor=cursor)
        cursor += pos
        md['sender'] = address_from_hash(md['sender'])
        pos, md['contractAddress'] = read_by_length(buffer, cursor=cursor)
        cursor += pos
        md['contractAddress'] = address_from_hash(md['contractAddress'])
        cursor, md['value'] = parse_varint(buffer, cursor)
        cursor, md['codeLen'] = parse_varint(buffer, cursor)
        pos, md['code'] = read_by_length(buffer, cursor=cursor)
        cursor += pos
        md['code'] = md['code'].hex()

        cursor, md['gasLimit'] = parse_varint(buffer, cursor)
        cursor, md['price'] = parse_varint(buffer, cursor)
        argslen = int(buffer[cursor])
        cursor += 1
        args = []
        for i in range(argslen):
            arglen = int(buffer[cursor])
            cursor += 1
            arg = []
            for j in range(arglen):
                pos, argcontent = read_by_length(buffer, cursor=cursor)
                cursor += pos
                arg.append(argcontent.decode('utf-8'))

            args.append(arg)

        md['args'] = args
        return cursor, md

    @classmethod
    async def to_buffer(cls, md):
        output = write_with_length(hash_from_address(md['sender']))
        output += write_with_length(hash_from_address(md['contractAddress']))
        output += write_varint(md['value'])
        output += write_varint(md['codeLen'])
        output += write_with_length(unhexlify(md['code']))
        output += write_varint(md['gasLimit'])
        output += write_varint(md['price'])
        output += bytes([len(md['args'])])
        for arg in md['args']:
            output += bytes([len(arg)])
            for argitem in arg:
                output += write_with_length(argitem.encode('utf-8'))
        return output

register_tx_type(100, CreateContractData)

class CallContractData(BaseModuleData):
    @classmethod
    async def from_buffer(cls, buffer, cursor=0):
        md = dict()
        pos, md['sender'] = read_by_length(buffer, cursor=cursor)
        cursor += pos
        md['sender'] = address_from_hash(md['sender'])
        pos, md['contractAddress'] = read_by_length(buffer, cursor=cursor)
        cursor += pos
        md['contractAddress'] = address_from_hash(md['contractAddress'])
        cursor, md['value'] = parse_varint(buffer, cursor)
        cursor, md['gasLimit'] = parse_varint(buffer, cursor)
        cursor, md['price'] = parse_varint(buffer, cursor)
        pos, md['methodName'] = read_by_length(buffer, cursor=cursor)
        md['methodName'] = md['methodName'].decode('utf-8')
        cursor += pos
        pos, md['methodDesc'] = read_by_length(buffer, cursor=cursor)
        md['methodDesc'] = md['methodDesc'].decode('utf-8')
        cursor += pos
        argslen = int(buffer[cursor])
        cursor += 1
        args = []
        for i in range(argslen):
            arglen = int(buffer[cursor])
            cursor += 1
            arg = []
            for j in range(arglen):
                pos, argcontent = read_by_length(buffer, cursor=cursor)
                cursor += pos
                arg.append(argcontent.decode('utf-8'))

            args.append(arg)

        md['args'] = args
        return cursor, md

    @classmethod
    async def to_buffer(cls, md):
        output = write_with_length(hash_from_address(md['sender']))
        output += write_with_length(hash_from_address(md['contractAddress']))
        output += write_varint(md['value'])
        output += write_varint(md['gasLimit'])
        output += write_varint(md['price'])
        output += write_with_length(md['methodName'].encode('utf-8'))
        output += write_with_length(md['methodDesc'].encode('utf-8'))
        output += bytes([len(md['args'])])
        for arg in md['args']:
            output += bytes([len(arg)])
            for argitem in arg:
                output += write_with_length(arg.encode('utf-8'))
        return output

register_tx_type(101, CallContractData)

class DeleteContractData(BaseModuleData):
    @classmethod
    async def from_buffer(cls, buffer, cursor=0):
        md = dict()
        pos, md['sender'] = read_by_length(buffer, cursor=cursor)
        cursor += pos
        md['sender'] = address_from_hash(md['sender'])
        pos, md['contractAddress'] = read_by_length(buffer, cursor=cursor)
        cursor += pos
        md['contractAddress'] = address_from_hash(md['contractAddress'])
        return cursor, md

    @classmethod
    async def to_buffer(cls, md):
        output = write_with_length(hash_from_address(md['sender']))
        output += write_with_length(hash_from_address(md['contractAddress']))
        return output

register_tx_type(102, DeleteContractData)

class TransferContractData(BaseModuleData):
    @classmethod
    async def from_buffer(cls, buffer, cursor=0):
        md = dict()
        return cursor, md

    @classmethod
    async def to_buffer(cls, md):
        return output

#register_tx_type(103, TransferContractData)
# not implemented for now...
