from nulsexplorer import model
import pymongo

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

def ensure_indexes(db):
    db.blocks.ensure_index([("hash", pymongo.ASCENDING)], unique=True)
    db.blocks.ensure_index([("height", pymongo.ASCENDING)], unique=True)
    db.blocks.ensure_index([("height", pymongo.DESCENDING)])
