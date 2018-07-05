from nulsexplorer import model
from nulsexplorer.model.base import BaseClass, Index
from nulsexplorer.model.transaction import Transaction
import pymongo

async def store_block(block_data):
    txs = block_data.pop("txList")
    doc_id = await model.db.blocks.insert_one(block_data)
    if len(txs):
        for transaction in txs:
            await Transaction.input_txdata(transaction)
        # for now we forget about bulk insert as we have to do some work on it...
        # await model.db.transactions.insert_many(txs)
    return doc_id

async def get_last_block():
    query = model.db.blocks.find().sort([('height', -1)]).limit(1)
    if await query.fetch_next:
        return query.next_object()
    else:
        return None

async def get_last_block_height():
    block = await get_last_block()
    if block is not None:
        return block['height']
    else:
        return None

async def find_block(query):
    return await model.db.blocks.find_one(query)

async def find_blocks(query, scrubbed=True, sort=None, limit=0):
    projection = None
    if scrubbed:
        projection = {'height':1,
                      'hash': 1,
                      'preHash': 1,
                      'txCount': 1,
                      'time': 1,
                      'packingAddress': 1,
                      'reward': 1,
                      'fee': 1,
                      'size': 1,
                      'scriptSig': 1}
    if sort is None:
        sort = [('height', 1)]

    return model.db.blocks.find(query, projection=projection, limit=limit).sort(sort)

class Block(BaseClass):
    COLLECTION = "blocks"

    INDEXES = [Index("hash", unique=True),
               Index("height", pymongo.ASCENDING, unique=True),
               Index("height", pymongo.DESCENDING)]
