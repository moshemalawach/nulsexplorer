from nulsexplorer.protocol.data import (write_with_length, read_by_length,
                                        hash_from_address)
from nulsexplorer.protocol.register import register_tx_type
from .base import BaseModuleData
from binascii import hexlify, unhexlify

class BusinessData(BaseModuleData):
    @classmethod
    async def from_buffer(cls, buffer, cursor=0):
        md = dict()
        pos, md['logicData'] = read_by_length(buffer, cursor)
        cursor += pos
        md['logicData'] =  md['logicData'].hex()
        return cursor, md

    @classmethod
    async def to_buffer(cls, md):
        output = write_with_length(unhexlify(md['logicData']))
        return output

register_tx_type(10, BusinessData)
