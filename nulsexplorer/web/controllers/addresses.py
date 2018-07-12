import aiohttp_jinja2
from nulsexplorer.web import app
from nulsexplorer.model.transactions import Transaction
from nulsexplorer.model.blocks import (get_last_block_height)
from .utils import Pagination, PER_PAGE

from aiocache import cached, SimpleMemoryCache

# WARNING: we are storing this in memory... memcached or similar would be better
#          if volume starts to be too big.
@cached(ttl=60*10, cache=SimpleMemoryCache) # 600 seconds or 10 minutes
async def addresses_unspent_txs():
    aggregate = Transaction.collection.aggregate([
        {'$unwind': '$outputs'}, {'$match': {'outputs.status': {'$lt': 3}}},
        {'$group': {'_id': '$outputs.address',
                    'unspent_count': {'$sum': 1},
                    'unspent_value': {'$sum': '$outputs.value'},
                    'locked_value': {'$sum': {"$cond": [
                        {"$eq": [
                            "$outputs.status",
                            2
                        ]},
                        "$outputs.value",
                        0
                    ]}},
                    'time_locked_value': {'$sum': {"$cond": [
                        {"$and": [
                            {"$eq": [
                                "$outputs.status",
                                2
                            ]},
                            {"$gt": [
                                "$outputs.lockTime",
                                0
                            ]}
                        ]},
                        "$outputs.value",
                        0
                    ]}}}},
        {'$sort': {'unspent_value': -1}}
    ])
    return [item async for item in aggregate]

@cached(ttl=60*10, cache=SimpleMemoryCache) # 600 seconds or 10 minutes
async def addresses_unspent_info():
    unspent_info = await addresses_unspent_txs()
    return {info['_id']: info
            for info in unspent_info}

@aiohttp_jinja2.template('address.html')
async def view_address(request):
    """ Address view
    """
    address = request.match_info['address']
    page = int(request.match_info.get('page', '1'))
    where_query = {'$or':
                    [{'outputs.address': address},
                     {'inputs.address': address}]}
    tx_count = await Transaction.count(where_query)

    transactions = [tx async for tx in Transaction.find(where_query,
                                                        sort='time',
                                                        sort_order=-1,
                                                        limit=PER_PAGE,
                                                        skip=(page-1)*PER_PAGE)]
    # reusing data from cache here... maybe we should do a search here too ?
    unspent_info = (await addresses_unspent_info()).get(address, {})

    pagination = Pagination(page, PER_PAGE, tx_count)

    return {'address': address,
            'transactions': transactions,
            'pagination': pagination,
            'unspent_info': unspent_info,
            'last_height': await get_last_block_height()}
app.router.add_get('/addresses/{address}', view_address)
app.router.add_get('/addresses/{address}/page/{page}', view_address)

@aiohttp_jinja2.template('addresses.html')
async def address_list(request):
    """ Addresses view
    """
    addresses = await addresses_unspent_txs()
    total_addresses = len(addresses)
    page = int(request.match_info.get('page', '1'))
    addresses = addresses[(page-1)*PER_PAGE:((page-1)*PER_PAGE)+PER_PAGE]

    pagination = Pagination(page, PER_PAGE, total_addresses)

    return {'addresses': addresses,
            'pagination': pagination,
            'last_height': await get_last_block_height()}
app.router.add_get('/addresses', address_list)
app.router.add_get('/addresses/page/{page}', address_list)
