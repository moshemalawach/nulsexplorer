import aiohttp_jinja2
from aiohttp import web
from nulsexplorer.web import app
from nulsexplorer.model.transactions import Transaction
from nulsexplorer.model.blocks import Block

async def search(request):
    """ Search view
    """
    query = request.query.get('q', '').strip()
    if (await Block.count({'hash': query})):
        raise web.HTTPFound('/blocks/%s' % query)
    elif (await Transaction.count({'hash': query})):
        raise web.HTTPFound('/transactions/%s' % query)
    elif (await Transaction.count({'$or':
                    [{'outputs.address': query},
                     {'inputs.address': query}]})):
        raise web.HTTPFound('/addresses/%s' % query)
    else:
        raise web.HTTPNotFound(text="Nothing found for that search")
app.router.add_get('/search', search)
