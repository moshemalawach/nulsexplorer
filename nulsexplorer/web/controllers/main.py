import pkg_resources
import aiohttp_jinja2

from aiohttp import web
from math import ceil
from nulsexplorer.web import app
from nulsexplorer.model.consensus import Consensus
from nulsexplorer.model.transactions import Transaction
from nulsexplorer.model.blocks import (Block, find_blocks, find_block,
                                       get_last_block_height)

PER_PAGE = 20

app.router.add_static('/static/',
                      path=pkg_resources.resource_filename('nulsexplorer.web', 'static/'),
                      name='static')

class Pagination(object):

    def __init__(self, page, per_page, total_count):
        self.page = page
        self.per_page = per_page
        self.total_count = total_count

    @property
    def pages(self):
        return int(ceil(self.total_count / float(self.per_page)))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and \
                num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num

@aiohttp_jinja2.template('index.html')
async def index(request):
    """Index of the block explorer.
    """
    last_blocks = [block async for block
                   in Block.find({}, limit=10, sort=[('height', -1)])]

    return {'last_blocks': last_blocks,
            'last_height': await get_last_block_height()}
app.router.add_get('/', index)

#@aiohttp_jinja2.template('search.html')
async def search(request):
    """ Search view
    """
    query = request.query.get('q', '')
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

    #return {'last_height': await get_last_block_height()}
app.router.add_get('/search', search)

@aiohttp_jinja2.template('block.html')
async def view_block(request):
    """ Block view
    """
    block_hash = request.match_info['block_hash']
    block = await find_block({'hash': block_hash})
    if block is None:
        raise web.HTTPNotFound(text="Block not found")

    transactions = [item async for item in Transaction.find({'blockHeight': block['height']})]

    return {'block': block,
            'transactions': transactions,
            'last_height': await get_last_block_height()}
app.router.add_get('/blocks/{block_hash}', view_block)

@aiohttp_jinja2.template('blocks.html')
async def block_list(request):
    """ Blocks view
    """

    total_blocks = await Block.count()
    page = int(request.match_info.get('page', '1'))
    blocks = [block async for block
              in Block.find({}, limit=PER_PAGE, skip=(page-1)*PER_PAGE,
                            sort=[('height', -1)])]

    pagination = Pagination(page, PER_PAGE, total_blocks)

    return {'blocks': blocks,
            'pagination': pagination,
            'last_height': await get_last_block_height()}
app.router.add_get('/blocks', block_list)
app.router.add_get('/blocks/page/{page}', block_list)

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

@aiohttp_jinja2.template('consensus.html')
async def consensus(request):
    """ Address view
    """
    last_height = await get_last_block_height()
    consensus = await Consensus.collection.find_one(sort=[('height', -1)])
    packed_block_query = {'$group' : { '_id' : '$packingAddress', 'count' : {'$sum' : 1}}}
    totals = Block.collection.aggregate([packed_block_query])
    totals_all = {r['_id']: r['count'] async for r in totals}
    totals = Block.collection.aggregate([
        {'$match': {'height': {'$gt': last_height-360}}},
        packed_block_query
    ])
    totals_hour = {r['_id']: r['count'] async for r in totals}
    totals = Block.collection.aggregate([
        {'$match': {'height': {'$gt': last_height-8640}}},
        packed_block_query
    ])
    totals_day = {r['_id']: r['count'] async for r in totals}
    #db.blocks.aggregate({$match: {'height': {'$gt': 40000}}},     )

    return {'consensus': consensus,
            'last_height': last_height,
            'total_all': totals_all,
            'total_hour': totals_hour,
            'total_day': totals_day}
app.router.add_get('/consensus', consensus)
