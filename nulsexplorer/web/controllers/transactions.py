import aiohttp_jinja2
from nulsexplorer.web import app
from nulsexplorer.model.transactions import Transaction
from nulsexplorer.model.blocks import (get_last_block_height, find_block)

@aiohttp_jinja2.template('transaction.html')
async def view_transaction(request):
    """ Transaction view
    """
    tx_hash = request.match_info['tx_hash']
    transaction = await Transaction.find_one(hash = tx_hash)
    if transaction is None:
        raise web.HTTPNotFound(text="Transaction not found")
    block = await find_block({'height': transaction.blockHeight})

    return {'block': block,
            'transaction': transaction,
            'last_height': await get_last_block_height()}
app.router.add_get('/transactions/{tx_hash}', view_transaction)
