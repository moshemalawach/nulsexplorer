import aiohttp_jinja2
from nulsexplorer.web import app
from nulsexplorer.model.transactions import Transaction
from nulsexplorer.model.blocks import (get_last_block_height)

@aiohttp_jinja2.template('address.html')
async def view_address(request):
    """ Address view
    """
    address = request.match_info['address']

    transactions = [tx async for tx in Transaction.find({'$or':
                    [{'outputs.address': address},
                     {'inputs.address': address}]}, sort='time', sort_order=-1)]

    return {'address': address,
            'transactions': transactions,
            'last_height': await get_last_block_height()}
app.router.add_get('/addresses/{address}', view_address)
