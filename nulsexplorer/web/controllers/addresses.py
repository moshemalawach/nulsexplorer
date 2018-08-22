import aiohttp_jinja2
from aiohttp import web
from collections import defaultdict
from nulsexplorer import TRANSACTION_TYPES
from nulsexplorer.web import app
from nulsexplorer.model.transactions import Transaction
from nulsexplorer.model.blocks import (get_last_block_height)
from bson import json_util
import datetime
import time
import json
from .utils import (Pagination, PER_PAGE, PER_PAGE_SUMMARY,
                    cond_output)

from aiocache import cached, SimpleMemoryCache

@cached(ttl=60*120, cache=SimpleMemoryCache)
async def cache_last_block_height():
    return await get_last_block_height()

# WARNING: we are storing this in memory... memcached or similar would be better
#          if volume starts to be too big.
@cached(ttl=60*120, cache=SimpleMemoryCache) # 60*120 seconds or 2 hours minutes
async def addresses_unspent_txs(last_block_height, check_time=None, address_list=None):
    t1 = datetime.datetime.now()
    if check_time is None:
        check_time = datetime.datetime.now()

    match_step = {'$match': {'outputs.status': {'$lt': 3}}}
    matches = [match_step]
    if address_list is not None:
        matches.append({
            '$match': {'outputs.address': {'$in': address_list}}
        })

    aggregate = Transaction.collection.aggregate(
        matches + [{'$unwind': '$outputs'}] + matches + [
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
    items = [item async for item in aggregate]
    t2 = datetime.datetime.now()
    print(t2-t1)
    return items

@cached(ttl=60*10, cache=SimpleMemoryCache) # 600 seconds or 10 minutes
async def addresses_unspent_info(last_block_height, address_list=None):
    unspent_info = await addresses_unspent_txs(last_block_height,
                                               address_list=address_list)
    return {info['_id']: info
            for info in unspent_info}

async def summarize_tx(tx, pov, node_mode=False):
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

    elif tx['type'] in [2, 3] and not node_mode:
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
        addr = inputs[0]['address']
        if tx['info'].get('address'):
            addr = tx['info']['address']

        tx['source'] = addr

        for o in outputs:
            if o['lockTime'] == -1:
                tx['value'] = o['value']
                break


    elif tx['type'] in [6, 9]:
        addr = inputs[0]['address']
        if tx['info'].get('address'):
            addr = tx['info']['address']

        if node_mode:
            tx['target'] = addr
        else:
            tx['source'] = addr

        tx['value'] = inputs[0]['value']
        if node_mode:
            tx['value'] = tx['value']*-1

    return tx


async def get_aliases():
    aggregate = Transaction.collection.aggregate([
         {'$match': {'type': 3}},
         {'$group': {'_id': '$info.alias',
                     'address': {'$last': {'$arrayElemAt': ['$inputs.address', 0]}},
                     'time': {'$last': '$time'},
                     'blockHeight': {'$last': '$blockHeight'}}},
         {'$sort': {'_id': 1}}])
    return [item async for item in aggregate]

#@aiohttp_jinja2.template('aliases.html')
async def aliases(request):
    """ Addresses view
    """
    last_height = await get_last_block_height()
    aliases = await get_aliases()
    total_aliases = len(aliases)
    page = int(request.match_info.get('page', '1'))
    aliases = aliases[(page-1)*PER_PAGE_SUMMARY:((page-1)*PER_PAGE_SUMMARY)+PER_PAGE_SUMMARY]

    pagination = Pagination(page, PER_PAGE_SUMMARY, total_aliases)

    context =  {'aliases': aliases,
            'pagination': pagination,
            'last_height': last_height,
            'pagination_page': page,
            'pagination_total': total_aliases,
            'pagination_per_page': PER_PAGE_SUMMARY,
            'pagination_item': 'aliases'}

    return cond_output(request, context, 'aliases.html')

app.router.add_get('/addresses/aliases.json', aliases)
app.router.add_get('/addresses/aliases', aliases)
app.router.add_get('/addresses/aliases/page/{page}.json', aliases)
app.router.add_get('/addresses/aliases/page/{page}', aliases)

#@aiohttp_jinja2.template('addresses.html')
async def address_list(request):
    """ Addresses view
    """
    last_height = await get_last_block_height()
    addresses = await addresses_unspent_txs(await cache_last_block_height())
    total_addresses = len(addresses)
    page = int(request.match_info.get('page', '1'))
    addresses = addresses[(page-1)*PER_PAGE_SUMMARY:((page-1)*PER_PAGE_SUMMARY)+PER_PAGE_SUMMARY]

    pagination = Pagination(page, PER_PAGE_SUMMARY, total_addresses)

    context = {'addresses': addresses,
              'pagination': pagination,
              'last_height': last_height,
              'pagination_page': page,
              'pagination_total': total_addresses,
              'pagination_per_page': PER_PAGE_SUMMARY,
              'pagination_item': 'addresses'}

    return cond_output(request, context, 'addresses.html')

app.router.add_get('/addresses', address_list)
app.router.add_get('/addresses.json', address_list)
app.router.add_get('/addresses/page/{page}', address_list)
app.router.add_get('/addresses/page/{page}.json', address_list)

#@aiohttp_jinja2.template('address.html')
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

    if request.rel_url.path.endswith('/all.json'):
        per_page = 10000

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

    transactions = [tx._data async for tx in Transaction.find(where_query,
                                                        sort='time',
                                                        sort_order=-1,
                                                        limit=per_page,
                                                        skip=(page-1)*per_page)]

    if "summary" in mode:
        transactions = [await summarize_tx(tx, address) for tx in transactions]
    # reusing data from cache here... maybe we should do a search here too ?
    #unspent_info = (await addresses_unspent_info(await cache_last_block_height())).get(address, {})
    unspent_info = (await addresses_unspent_info(last_height,
                                                 address_list=[address])
                    ).get(address, {})

    pagination = Pagination(page, per_page, tx_count)

    context = {'address': address,
               'transactions': transactions,
               'pagination': pagination,
               'unspent_info': unspent_info,
               'last_height': last_height,
               'tx_count': tx_count,
               'mode': mode,
               'pagination_page': page,
               'pagination_total': tx_count,
               'pagination_per_page': per_page,
               'pagination_item': 'transactions'}

    return cond_output(request, context, 'address.html')



async def address_available_outputs(request):
    """ Returns the unspent available outputs for a given address.
    Useful for light wallets.
    """
    last_height = await get_last_block_height()
    check_time = datetime.datetime.now()
    db_time = int(time.mktime(check_time.timetuple())*1000)
    address = request.match_info['address']
    all_txs = Transaction.collection.find(
            {'outputs.status': {'$lt': 3},
             'outputs.address': address})
    unspent_info = (await addresses_unspent_info(last_height,
                                                 address_list=[address])
                    ).get(address, {})
    outputs = []
    async for tx in all_txs:
        tx_hash = tx['hash']
        for idx, output in enumerate(tx['outputs']):
            lock_time = output['lockTime']
            if output['address'] != address:
                continue

            if output['status'] >= 3:
                continue # spent

            if lock_time == -1:
                continue # consensus locked

            if (lock_time < 1000000000000) and (lock_time > last_height):
                continue # time locked on a future block

            if lock_time > db_time:
                continue # time locked on a future time

            outputs.append({
                'hash': tx_hash,
                'idx': idx,
                'value': output['value']
            })

    context = {'outputs': outputs,
               'last_height': last_height,
               'unspent_info': unspent_info,
               'total_available': sum([o['value'] for o in outputs])}
    return web.json_response(context, dumps=lambda v: json.dumps(v,
                                                     default=json_util.default))

app.router.add_get('/addresses/outputs/{address}.json', address_available_outputs)

app.router.add_get('/addresses/{address}.json', view_address)
app.router.add_get('/addresses/{address}', view_address)
app.router.add_get('/addresses/{address}/{mode}.json', view_address)
app.router.add_get('/addresses/{address}/{mode}', view_address)
app.router.add_get('/addresses/{address}/page/{page}.json', view_address)
app.router.add_get('/addresses/{address}/page/{page}', view_address)
app.router.add_get('/addresses/{address}/{mode}/page/{page}.json', view_address)
app.router.add_get('/addresses/{address}/{mode}/page/{page}', view_address)
app.router.add_get('/addresses/{address}/{mode}/all.json', view_address)
