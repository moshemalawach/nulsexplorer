import aiohttp_jinja2
from nulsexplorer.web import app
from nulsexplorer.model.transactions import Transaction
from nulsexplorer.model.blocks import (get_last_block_height, find_block)
from .utils import Pagination, PER_PAGE, cond_output
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
