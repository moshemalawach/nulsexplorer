import pkg_resources
import aiohttp_jinja2

from aiohttp import web
from nulsexplorer.web import app
from nulsexplorer.model.blocks import (find_blocks, find_block,
                                       get_last_block_height)

app.router.add_static('/static/',
                      path=pkg_resources.resource_filename('nulsexplorer.web', 'static/'),
                      name='static')

@aiohttp_jinja2.template('index.html')
async def index(request):
    """Index of the block explorer.
    """
    last_blocks = []
    async for block in await find_blocks({}, scrubbed=True, limit=5, sort=[('height', -1)]):
        last_blocks.append(block)

    return {'last_blocks': last_blocks,
            'last_height': await get_last_block_height()}
app.router.add_get('/', index)

@aiohttp_jinja2.template('block.html')
async def view_block(request):
    """Index of the block explorer.
    """
    block_hash = request.match_info['block_hash']
    block = await find_block({'hash': block_hash})
    if block is None:
        raise web.HTTPNotFound(text="Block not found")

    return {'block': block,
            'last_height': await get_last_block_height()}
app.router.add_get('/blocks/{block_hash}', view_block)
