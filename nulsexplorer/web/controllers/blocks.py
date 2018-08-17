import aiohttp_jinja2
from nulsexplorer.web import app
from nulsexplorer.model.transactions import Transaction
from nulsexplorer.model.blocks import (Block, find_blocks, find_block,
                                       get_last_block_height)
from aiohttp import web
from .utils import Pagination, PER_PAGE, cond_output, prepare_date_filters, prepare_block_height_filters
import logging

LOGGER = logging.getLogger(__name__)


#@aiohttp_jinja2.template('block.html')
async def view_block(request):
    """ Block view
    """
    block_hash = request.match_info['block_hash']
    block = await find_block({'hash': block_hash})
    page = int(request.match_info.get('page', '1'))
    if block is None:
        raise web.HTTPNotFound(text="Block not found")

    transactions = [item._data async
                    for item in Transaction.find({'blockHeight': block['height']},
                                                 limit=PER_PAGE,
                                                 skip=(page-1)*PER_PAGE)]
    pagination = Pagination(page, PER_PAGE, block['txCount'])

    context = {'block': block,
                'pagination': pagination,
                'transactions': transactions,
                'last_height': await get_last_block_height(),
                'pagination_page': page,
                'pagination_total': block['txCount'],
                'pagination_per_page': PER_PAGE,
                'pagination_item': 'transactions'}

    return cond_output(request, context, 'block.html')

app.router.add_get('/blocks/{block_hash}.json', view_block)
app.router.add_get('/blocks/{block_hash}', view_block)
app.router.add_get('/blocks/{block_hash}/page/{page}.json', view_block)
app.router.add_get('/blocks/{block_hash}/page/{page}', view_block)

#@aiohttp_jinja2.template('blocks.html')
async def block_list(request):
    """ Blocks view
    """

    find_filters = {}
    filters = []

    query_string = request.query_string
    producer = request.query.get('producer', None)
    date_filters = prepare_date_filters(request, 'time')
    block_height_filters = prepare_block_height_filters(request, 'height')

    if producer is not None:
        filters.append({'packingAddress': producer})

    if date_filters is not None:
        filters.append(date_filters)

    if block_height_filters is not None:
        filters.append(block_height_filters)

    if len(filters) > 0:
        find_filters = {'$and': filters} if len(filters) > 1 else filters[0]

    pagination_page, pagination_per_page, pagination_skip = Pagination.get_pagination_params(request)

    blocks = [block._data async for block
              in Block.find(find_filters, limit=pagination_per_page, skip=pagination_skip,
                            sort=[('height', -1)])]

    context = {'blocks': blocks,
                'last_height': await get_last_block_height()}

    if pagination_per_page is not None:
        total_blocks = await Block.count(find_filters)

        pagination = Pagination(pagination_page, pagination_per_page, total_blocks, 
                                url_base='/blocks/page/', query_string=query_string)
                                
        context.update({
            'pagination': pagination,
            'pagination_page': pagination_page,
            'pagination_total': total_blocks,
            'pagination_per_page': pagination_per_page,
            'pagination_item': 'blocks'
        })

    return cond_output(request, context, 'blocks.html')

app.router.add_get('/blocks.json', block_list)
app.router.add_get('/blocks', block_list)
app.router.add_get('/blocks/page/{page}.json', block_list)
app.router.add_get('/blocks/page/{page}', block_list)
