import asyncio
import aiohttp
import logging
import base64
import operator

from aiohttp import web, ClientSession

from nulsexplorer.web import app
from nulsexplorer import model
from nulsexplorer.model.blocks import get_last_block_height, store_block
from nulsexplorer.model.transactions import Transaction
from nulsexplorer.model.consensus import Consensus
from nulsexplorer.protocol.block import Block

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

async def api_post(session, uri, data):
    base_uri = app['config'].nuls.base_uri.value
    async with session.post(base_uri + uri, json=data) as resp:
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

async def request_block(session, height=None, hash=None, use_bytes=True):
    last_height = -1
    block = {}
    if height is not None:
        resp = await api_request(session, 'block/header/height/%d' % height)
        block = resp
        hash = resp['hash']

    if hash is not None:
        if use_bytes:
            resp = await api_request(session, 'block/bytes?hash=%s' % hash)
            #if any([tx["type"] > 2 for tx in block["txList"]]):
                # only parse full block if needed...
            try:
                block_obj = Block(hash_switch_height=app['config'].nuls.hash_switch_height.value)
                await block_obj.parse(base64.b64decode(resp['value']))
                block.update(await block_obj.to_dict())
            except Exception as e:
                LOGGER.error("Error reading block %d" % height)
                LOGGER.exception(e)
                LOGGER.info("Using block content %r instead." % block)
                raise
    else:
        raise ValueError("Neither height nor hash set for block request")

    return block


async def request_consensus(session):
    resp = await api_request(session, 'consensus/agent/list?pageSize=100')
    nodes = resp['list']
    if resp['pages'] > 1:
        for i in range(2, resp['pages']+1):
            resp = await api_request(
                session,
                'consensus/agent/list?pageSize=100&pageNumber=%d' % i)
            nodes += resp['list']
    return nodes


async def check_blocks():
    last_stored_height = await get_last_block_height()
    last_height = -1
    if last_stored_height is None:
        last_stored_height = -1

    big_batch = False
    LOGGER.info("Last block is #%d" % last_stored_height)
    while True:
        async with aiohttp.ClientSession() as session:
            last_height = await request_last_height(session)
            big_batch = False
            if (last_height - last_stored_height) > 1000:
                big_batch = True

            if last_height > last_stored_height:
                consensus_nodes = await request_consensus(session)
                await Consensus.collection.replace_one(
                    {'height': last_height},
                    {'height': last_height,
                     'agents': consensus_nodes},
                     upsert=True)

                batch_blocks = dict()
                batch_transactions = dict()

                for i, block_height in enumerate(range(last_stored_height+1, last_height+1)):
                    try:
                        block = await request_block(session, height=block_height)
                        LOGGER.info("Synchronizing block #%d" % block['height'])
                        # if we are working on a big batch, don't save in db yet
                        # add to a big dict instead
                        await store_block(block, big_batch=big_batch,
                                          batch_blocks=batch_blocks,
                                          batch_transactions=batch_transactions)
                    except OverflowError:
                        LOGGER.error("Error storing block #%d" % block['height'])
                        LOGGER.info("Using upstream data for block #%d" % block['height'])
                        block = await request_block(session, height=block_height, use_bytes=False)
                        await store_block(block)
                    last_stored_height = block['height']

                    if i > 100000:
                        break

                if big_batch:
                    await model.db.blocks.insert_many(
                        sorted(batch_blocks.values(),
                               key=operator.itemgetter('height')))
                    await model.db.transactions.insert_many(
                        sorted(batch_transactions.values(),
                               key=operator.itemgetter('blockHeight')))
        if not big_batch:
            # we sleep only if we are not in the middle of a big batch
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
