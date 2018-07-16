import aiohttp_jinja2
from aiohttp import web
from collections import defaultdict
from nulsexplorer import TRANSACTION_TYPES
from nulsexplorer.web import app
from nulsexplorer.model.transactions import Transaction
from nulsexplorer.model.blocks import (get_last_block_height)
import datetime
import time
from .utils import Pagination, PER_PAGE, PER_PAGE_SUMMARY

from aiocache import cached, SimpleMemoryCache

@cached(ttl=60*10, cache=SimpleMemoryCache)
async def cache_last_block_height():
    return await get_last_block_height()

# WARNING: we are storing this in memory... memcached or similar would be better
#          if volume starts to be too big.
@cached(ttl=60*10, cache=SimpleMemoryCache) # 600 seconds or 10 minutes
async def addresses_unspent_txs(last_block_height, check_time=None):
    if check_time is None:
        check_time = datetime.datetime.now()

    aggregate = Transaction.collection.aggregate([
        {'$unwind': '$outputs'}, {'$match': {'outputs.status': {'$lt': 3}}},
        {'$group': {'_id': '$outputs.address',
                    'unspent_count': {'$sum': 1},
                    'unspent_value': {'$sum': '$outputs.value'},
                    'consensus_locked_value': {'$sum': {"$cond": [
                        {"$and": [
                            {"$lt": [
                                "$outputs.status",
                                3
                            ]},
                            {"$eq": [
                                "$outputs.lockTime",
                                -1
                            ]}
                        ]},
                        "$outputs.value",
                        0
                    ]}},
                    'time_locked_value': {'$sum': {"$cond": [
                        {"$and": [
                            {"lt": [
                                "$outputs.status",
                                3
                            ]},
                            {"$gt": [
                                "$outputs.lockTime",
                                0
                            ]},
                            {"$or": [
                                {"$and": [
                                    {"$lt": [
                                        "$outputs.lockTime",
                                        1000000000000
                                    ]},
                                    {"$gt": [
                                        "$outputs.lockTime",
                                        last_block_height
                                    ]}
                                ]},
                                {"$and": [
                                    {"$gt": [
                                        "$outputs.lockTime",
                                        1000000000000
                                    ]},
                                    {"$gt": [
                                        "$outputs.lockTime",
                                        int(time.mktime(check_time.timetuple())*1000)
                                    ]}
                                ]},
                            ]}
                        ]},
                        "$outputs.value",
                        0
                    ]}}
                    }},
        {'$addFields': {
            'locked_value': {'$add': ['$time_locked_value', '$consensus_locked_value']},
        }},
        {'$addFields': {
            'available_value': {'$subtract': ['$unspent_value', '$locked_value']}
        }},
        {'$sort': {'unspent_value': -1}}
    ])
    return [item async for item in aggregate]

@cached(ttl=60*10, cache=SimpleMemoryCache) # 600 seconds or 10 minutes
async def addresses_unspent_info(last_block_height):
    unspent_info = await addresses_unspent_txs(last_block_height)
    return {info['_id']: info
            for info in unspent_info}

async def summarize_tx(tx, pov):
    """ Summarizes a TX, trying to understand the context.
    POV is an address as the point of view.
    """
    tx['is_complex'] = False
    tx['display_type'] = TRANSACTION_TYPES[tx['type']].capitalize()
    tx['value'] = None
    tx['source'] = None
    tx['target'] = None
    inputs = tx['inputs']
    outputs = tx['outputs']

    input_values = defaultdict(int)
    output_values = defaultdict(int)
    for i in inputs:
        input_values[i['address']] += i['value']
    for o in outputs:
        output_values[o['address']] += o['value']

    if len(input_values.keys()) > 1:
        tx['is_complex'] = True
        tx['display_type'] = 'Complex'

    if tx['type'] == 1:
        tx['display_type'] = 'Reward'
        tx['value'] = output_values[pov]
        tx['target'] = pov

    elif tx['type'] in [2, 3]:
        tx['value'] = (output_values[pov] - input_values[pov])
        if tx['value'] > 0:
            if tx['type'] == 2:
                tx['display_type'] = 'IN'
            tx['source'] = inputs[0]['address']
            tx['target'] = pov
        elif tx['value'] < 1:
            if tx['type'] == 2:
                tx['display_type'] = 'OUT'
            tx['source'] = pov
            if len(output_values.keys()) <= 2:
                for addr, val in output_values.items():
                    if addr != pov:
                        tx['target'] = addr
                        break
        else:
            tx['display_type'] = '???'

    elif tx['type'] in [4, 5]:
        for o in outputs:
            if o['lockTime'] == -1:
                tx['value'] = o['value']
                break

    elif tx['type'] in [6, 9]:
        tx['value'] = inputs[0]['value']

    return tx


@aiohttp_jinja2.template('addresses.html')
async def address_list(request):
    """ Addresses view
    """
    last_height = await get_last_block_height()
    addresses = await addresses_unspent_txs(await cache_last_block_height())
    total_addresses = len(addresses)
    page = int(request.match_info.get('page', '1'))
    addresses = addresses[(page-1)*PER_PAGE_SUMMARY:((page-1)*PER_PAGE_SUMMARY)+PER_PAGE_SUMMARY]

    pagination = Pagination(page, PER_PAGE_SUMMARY, total_addresses)

    return {'addresses': addresses,
            'pagination': pagination,
            'last_height': last_height}
app.router.add_get('/addresses', address_list)
app.router.add_get('/addresses/page/{page}', address_list)

@aiohttp_jinja2.template('address.html')
async def view_address(request):
    """ Address view
    """
    last_height = await get_last_block_height()
    address = request.match_info['address']
    mode = request.match_info.get('mode', 'summary')
    if mode not in ['summary', 'full-summary', 'detail']:
        raise web.HTTPNotFound(text="Display mode not found")
    per_page = PER_PAGE
    if "summary" in mode:
        per_page = PER_PAGE_SUMMARY

    page = int(request.match_info.get('page', '1'))
    where_query = {'$or':
                    [{'outputs.address': address},
                     {'inputs.address': address}]}

    if mode == "summary":
        where_query = {'$and': [
            {'type': {'$ne': 1}},
            where_query
        ]}
    tx_count = await Transaction.count(where_query)

    transactions = [tx async for tx in Transaction.find(where_query,
                                                        sort='time',
                                                        sort_order=-1,
                                                        limit=per_page,
                                                        skip=(page-1)*per_page)]

    if "summary" in mode:
        transactions = [await summarize_tx(tx, address) for tx in transactions]
    # reusing data from cache here... maybe we should do a search here too ?
    unspent_info = (await addresses_unspent_info(await cache_last_block_height())).get(address, {})

    pagination = Pagination(page, per_page, tx_count)

    return {'address': address,
            'transactions': transactions,
            'pagination': pagination,
            'unspent_info': unspent_info,
            'last_height': last_height,
            'tx_count': tx_count,
            'mode': mode}

app.router.add_get('/addresses/{address}', view_address)
app.router.add_get('/addresses/{address}/{mode}', view_address)
app.router.add_get('/addresses/{address}/page/{page}', view_address)
app.router.add_get('/addresses/{address}/{mode}/page/{page}', view_address)
