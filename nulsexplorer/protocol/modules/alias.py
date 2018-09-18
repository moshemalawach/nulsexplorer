from nulsexplorer.protocol.data import (write_with_length, read_by_length,
                                        hash_from_address)
from nulsexplorer.protocol.register import register_tx_type
from .base import BaseModuleData

class AliasData(BaseModuleData):
    @classmethod
    async def from_buffer(cls, buffer, cursor=0):
        md = dict()
        pos, md['address'] = read_by_length(buffer, cursor)
        cursor += pos

        pos, md['alias'] = read_by_length(buffer, cursor)
        cursor += pos
        md['alias'] = md['alias'].decode('utf-8')
        return cursor, md

    @classmethod
    async def to_buffer(cls, md):
        output = write_with_length(hash_from_address(md['address']))
        output += write_with_length(md['alias'].encode('utf-8'))
        return output

register_tx_type(3, AliasData)
