import aiohttp_jinja2
from nulsexplorer.web import app
from nulsexplorer.model.transactions import Transaction
from nulsexplorer.model.blocks import (get_last_block_height, find_block)
from .utils import Pagination, PER_PAGE, cond_output, prepare_date_filters, prepare_block_height_filters
from aiohttp import web

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

    if len(filters) > 0:
        find_filters = {'$and': filters} if len(filters) > 1 else filters[0]

    pagination_page, pagination_per_page, pagination_skip = Pagination.get_pagination_params(request)

    transactions = [tx._data async for tx
                    in Transaction.find(find_filters, limit=pagination_per_page, skip=pagination_skip, sort=[('blockHeight', -1)])]

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
