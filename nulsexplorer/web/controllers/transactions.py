import time
import aiohttp_jinja2
from aiohttp import web
from aiocache import cached, SimpleMemoryCache

from nulsexplorer.web import app
from nulsexplorer.model.transactions import Transaction
from nulsexplorer.model.blocks import (get_last_block_height, find_block)
from .utils import Pagination, PER_PAGE, cond_output, prepare_date_filters, prepare_block_height_filters


#@aiohttp_jinja2.template('transaction.html')
async def view_transaction(request):
    """ Transaction view
    """
    tx_hash = request.match_info['tx_hash']
    transaction = await Transaction.find_one(hash = tx_hash)
    if transaction is None:
        raise web.HTTPNotFound(text="Transaction not found")
    block = await find_block({'height': transaction.blockHeight})

    context = {'block': block,
            'transaction': transaction._data,
            'last_height': await get_last_block_height()}

    return cond_output(request, context, 'transaction.html')
app.router.add_get('/transactions/{tx_hash}.json', view_transaction)
app.router.add_get('/transactions/{tx_hash}', view_transaction)


async def view_transaction_list(request):
    """ Transaction list view with filters
    """

    find_filters = {}
    filters = []

    query_string = request.query_string
    address = request.query.get('address', None)
    tx_type = request.query.get('type', None)
    mask_by_address = request.query.get('maskByAddress', None)
    date_filters = prepare_date_filters(request, 'time')
    block_height_filters = prepare_block_height_filters(request, 'blockHeight')

    if address is not None:
        filters.append({
            '$or': [
                {'outputs.address': address},
                {'inputs.address': address}
            ]
        })
    else:
        tx_from = request.query.get('from', None)
        if tx_from is not None:
            filters.append({'inputs.address': tx_from})

        tx_to = request.query.get('to', None)
        if tx_to is not None:
            filters.append({'outputs.address': tx_to})

    if tx_type is not None:
        filters.append({'type': int(tx_type)})

    if date_filters is not None:
        filters.append(date_filters)

    if block_height_filters is not None:
        filters.append(block_height_filters)

    if request.query.get('business_ipfs', None):
        # to get all busines data or ipfs related data
        filters.append({'$or': [
            {'info.type': 'ipfs'},
            {'type': 10}
        ]})

    if len(filters) > 0:
        find_filters = {'$and': filters} if len(filters) > 1 else filters[0]

    pagination_page, pagination_per_page, pagination_skip = Pagination.get_pagination_params(request)
    if pagination_per_page is None:
        pagination_per_page = 0
    if pagination_skip is None:
        pagination_skip = 0

    sort = [('blockHeight', int(request.query.get('sort_order', '-1')))]

    transactions = [tx async for tx
                    in Transaction.collection.find(find_filters, limit=pagination_per_page,
                    skip=pagination_skip, sort=sort)]

    if mask_by_address is not None:
        for tx in transactions:
            tx['inputs'] = list(filter(lambda i: i['address'] == mask_by_address, tx['inputs']))
            tx['outputs'] = list(filter(lambda o: o['address'] == mask_by_address, tx['outputs']))

    context = {
        'transactions': transactions,
        'last_height': await get_last_block_height()
    }

    if pagination_per_page is not None:
        total_txs = await Transaction.count(find_filters)

        pagination = Pagination(pagination_page, pagination_per_page, total_txs,
                                url_base='/transactions/page/', query_string=query_string)

        context.update({
            'pagination': pagination,
            'pagination_page': pagination_page,
            'pagination_total': total_txs,
            'pagination_per_page': pagination_per_page,
            'pagination_item': 'transactions'
        })

    return cond_output(request, context, 'TODO.html')

app.router.add_get('/transactions.json', view_transaction_list)
app.router.add_get('/transactions/page/{page}.json', view_transaction_list)

@cached(ttl=60*15, cache=SimpleMemoryCache, timeout=120) # 15 minutes ttl
async def get_history(period, min_time=None):
    if min_time is None:
        # if we don't have a min time, assume 30 days.
        min_time = (int(time.time())-(60*60*24*30))*1000
    max_time = int(time.time())*1000

    stages = [
        {'$sort': {'time': -1}},
        {'$match': {
            'time': {'$gt': min_time}
        }},
        {'$match': {
            'time': {'$lt': max_time}
        }}
    ]


    dateformat = None
    if period == "day":
        dateformat = "%Y-%m-%d"
    elif period == "hour":
        dateformat = "%Y-%m-%dT%H:00:00"
    elif period == "minute":
        dateformat = "%Y-%m-%dT%H:%M:00"
    else:
        raise NotImplementedError("Period type not implemented")

    stages.append({
        '$addFields': {
           'totalInputs': { '$sum': "$inputs.value" } ,
           'totalOutputs': { '$sum': "$outputs.value" }
        }
    })

    stages.append(
        { "$group": {
            "_id": {
                "$dateToString": {
                    "format": dateformat,
                    "date": {
                        "$toDate": '$time'
                    }
                }
            },
            "count": { "$sum": 1 },
            "output_value": { "$sum": "$totalOutputs" },
            "input_value": { "$sum": "$totalInputs" }
        } }
    )
    stages.append({'$sort': {'_id': 1}})
    result = Transaction.collection.aggregate(stages)
    return [stat async for stat in result]

async def histo(request):
    period = request.match_info['period']
    history = await get_history(period)

    context = {
        'stats': history
    }
    return cond_output(request, context, 'TODO.html')
app.router.add_get('/transactions/stats/{period}.json', histo)
