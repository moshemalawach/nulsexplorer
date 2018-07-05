import asyncio
import aiohttp
import logging
from nulsexplorer.web import app
from nulsexplorer import model
from nulsexplorer.model.blocks import get_last_block_height
from nulsexplorer.model.transactions import Transaction

LOGGER = logging.getLogger('connector')

async def api_request(session, uri):
    base_uri = app['config'].nuls.base_uri.value
    async with session.get(base_uri + uri) as resp:
        jres = await resp.json()
        if jres.get('success', False):
            return jres['data']
        else:
            print(repr(jres))
            return None # we got an error, we should log it correctly and catch it.

async def request_last_height(session):
    last_height = -1
    resp = await api_request(session, 'block/newest/height')
    if resp is not None:
        last_height = resp.get('value', -1)
    return last_height

async def request_block(session, height=None, hash=None):
    last_height = -1
    if height is not None:
        resp = await api_request(session, 'block/height/%d' % height)
    elif hash is not None:
        resp = await api_request(session, 'block/hash/%s' % hash)
    else:
        raise ValueError("Neither height nor hash set for block request")

    return resp

async def store_block(block_data):
    doc_id = await model.db.blocks.insert_one(block_data)
    if len(block_data['txList']):
        await model.db.transactions.insert_many(block_data['txList'])
    return doc_id

async def check_blocks():
    last_stored_height = await get_last_block_height()
    last_height = -1
    if last_stored_height is None:
        last_stored_height = -1

    LOGGER.info("Last block is #%d" % last_stored_height)
    while True:
        async with aiohttp.ClientSession() as session:
            last_height = await request_last_height(session)

            if last_height > last_stored_height:
                for block_height in range(last_stored_height+1, last_height+1):
                    block = await request_block(session, height=block_height)
                    LOGGER.info("Synchronizing block #%d" % block['height'])
                    await store_block(block)
                    last_stored_height = block['height']

        await asyncio.sleep(8)

async def worker():
    while True:
        try:
            await check_blocks()
        except:
            LOGGER.exception("ERROR, relagunching in 10 seconds")
            await asyncio.sleep(10)

def start_connector():
    loop = asyncio.get_event_loop()
    loop.create_task(worker())
