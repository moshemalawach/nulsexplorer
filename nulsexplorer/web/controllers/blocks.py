import aiohttp_jinja2
from nulsexplorer.web import app
from nulsexplorer.model.transactions import Transaction
from nulsexplorer.model.blocks import (Block, find_blocks, find_block,
                                       get_last_block_height)
from .utils import Pagination, PER_PAGE



@aiohttp_jinja2.template('block.html')
async def view_block(request):
    """ Block view
    """
    block_hash = request.match_info['block_hash']
    block = await find_block({'hash': block_hash})
    page = int(request.match_info.get('page', '1'))
    if block is None:
        raise web.HTTPNotFound(text="Block not found")

    transactions = [item async
                    for item in Transaction.find({'blockHeight': block['height']},
                                                 limit=PER_PAGE,
                                                 skip=(page-1)*PER_PAGE)]
    pagination = Pagination(page, PER_PAGE, block['txCount'])

    return {'block': block,
            'pagination': pagination,
            'transactions': transactions,
            'last_height': await get_last_block_height()}
app.router.add_get('/blocks/{block_hash}', view_block)
app.router.add_get('/blocks/{block_hash}/page/{page}', view_block)

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
