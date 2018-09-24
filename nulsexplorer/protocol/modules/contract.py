from nulsexplorer.protocol.data import (write_with_length, read_by_length,
                                        hash_from_address, address_from_hash,
                                        VarInt,
                                        parse_varint, write_varint,
                                        PLACE_HOLDER, ADDRESS_LENGTH, HASH_LENGTH)
from nulsexplorer.protocol.register import register_tx_type, register_tx_processor
from .base import BaseModuleData

import struct
import logging
LOGGER = logging.getLogger('contract_module')


# Reference implementation:
# https://github.com/nuls-io/nuls/blob/develop/contract-module/contract/src/main/java/io/nuls/contract/entity/txdata/CreateContractData.java
class CreateContractData(BaseModuleData):
    @classmethod
    async def from_buffer(cls, buffer, cursor=0):
        md = dict()

        md['sender'] = buffer[cursor:cursor+ADDRESS_LENGTH]
        cursor += ADDRESS_LENGTH
        md['sender'] = address_from_hash(md['sender'])

        md['contractAddress'] = buffer[cursor:cursor+ADDRESS_LENGTH]
        cursor += ADDRESS_LENGTH
        md['contractAddress'] = address_from_hash(md['contractAddress'])

        md['value'] = struct.unpack("q", buffer[cursor:cursor+8])[0]
        cursor += 8
        md['codeLen'] = struct.unpack("I", buffer[cursor:cursor+4])[0]
        cursor += 4
        pos, md['code'] = read_by_length(buffer, cursor=cursor)
        cursor += pos
        md['code'] = md['code'].hex()

        md['gasLimit'] = struct.unpack("q", buffer[cursor:cursor+8])[0]
        cursor += 8
        md['price'] = struct.unpack("q", buffer[cursor:cursor+8])[0]
        cursor += 8
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
                try:
                    argcontent = argcontent.decode('utf-8')
                except UnicodeDecodeError:
                    LOGGER.warning("Unicode decode error here, passing raw value.")
                arg.append(argcontent)

            args.append(arg)

        md['args'] = args
        return cursor, md

    @classmethod
    async def to_buffer(cls, md):
        output = hash_from_address(md['sender'])
        output += hash_from_address(md['contractAddress'])
        output += struct.pack("q", md['value'])
        output += struct.pack("I", md['codeLen'])
        output += write_with_length(unhexlify(md['code']))
        output += struct.pack("q", md['gasLimit'])
        output += struct.pack("q", md['price'])
        output += bytes([len(md['args'])])
        for arg in md['args']:
            output += bytes([len(arg)])
            for argitem in arg:
                try:
                    argitem = argitem.encode('utf-8')
                except UnicodeEncodeError:
                    LOGGER.warning("Unicode encode error here, passing raw value.")
                output += write_with_length(argitem)
        return output

register_tx_type(100, CreateContractData)

class CallContractData(BaseModuleData):
    @classmethod
    async def from_buffer(cls, buffer, cursor=0):
        md = dict()

        md['sender'] = buffer[cursor:cursor+ADDRESS_LENGTH]
        cursor += ADDRESS_LENGTH
        md['sender'] = address_from_hash(md['sender'])

        md['contractAddress'] = buffer[cursor:cursor+ADDRESS_LENGTH]
        cursor += ADDRESS_LENGTH
        md['contractAddress'] = address_from_hash(md['contractAddress'])

        md['value'] = struct.unpack("q", buffer[cursor:cursor+8])[0]
        cursor += 8
        md['gasLimit'] = struct.unpack("q", buffer[cursor:cursor+8])[0]
        cursor += 8
        md['price'] = struct.unpack("q", buffer[cursor:cursor+8])[0]
        cursor += 8

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
                try:
                    argcontent = argcontent.decode('utf-8')
                except UnicodeDecodeError:
                    LOGGER.warning("Unicode decode error here, passing raw value.")
                arg.append(argcontent)

            args.append(arg)

        md['args'] = args
        return cursor, md

    @classmethod
    async def to_buffer(cls, md):
        output = hash_from_address(md['sender'])
        output += hash_from_address(md['contractAddress'])
        output += struct.pack("q", md['value'])
        output += struct.pack("q", md['gasLimit'])
        output += struct.pack("q", md['price'])
        output += write_with_length(md['methodName'].encode('utf-8'))
        output += write_with_length(md['methodDesc'].encode('utf-8'))
        output += bytes([len(md['args'])])
        for arg in md['args']:
            output += bytes([len(arg)])
            for argitem in arg:
                try:
                    argitem = argitem.encode('utf-8')
                except UnicodeEncodeError:
                    LOGGER.warning("Unicode encode error here, passing raw value.")
                output += write_with_length(argitem)
        return output

register_tx_type(101, CallContractData)

class DeleteContractData(BaseModuleData):
    @classmethod
    async def from_buffer(cls, buffer, cursor=0):
        md = dict()

        md['sender'] = buffer[cursor:cursor+ADDRESS_LENGTH]
        cursor += ADDRESS_LENGTH
        md['sender'] = address_from_hash(md['sender'])

        md['contractAddress'] = buffer[cursor:cursor+ADDRESS_LENGTH]
        cursor += ADDRESS_LENGTH
        md['contractAddress'] = address_from_hash(md['contractAddress'])
        return cursor, md

    @classmethod
    async def to_buffer(cls, md):
        output = hash_from_address(md['sender'])
        output += hash_from_address(md['contractAddress'])
        return output

register_tx_type(102, DeleteContractData)

class TransferContractData(BaseModuleData):
    @classmethod
    async def from_buffer(cls, buffer, cursor=0):
        md = dict()
        md['originTxHash'] = buffer[cursor:cursor+HASH_LENGTH].hex()
        cursor += HASH_LENGTH

        md['contractAddress'] = buffer[cursor:cursor+ADDRESS_LENGTH]
        cursor += ADDRESS_LENGTH
        md['contractAddress'] = address_from_hash(md['contractAddress'])

        md['success'] = int(buffer[cursor])
        cursor += 1

        return cursor, md

    @classmethod
    async def to_buffer(cls, md):
        output = unhexlify(md['originTxHash'])
        output += hash_from_address(md['contractAddress'])
        output += bytes([len(md['success'])])

        return output

register_tx_type(103, TransferContractData)


async def process_contract_data(tx):
    # This function takes a tx dict and modifies it in place.
    # we assume we have access to a config since we are in a processor
    from nulsexplorer.main import api_request


register_tx_processor([100,101,102,103], process_contract_data)
