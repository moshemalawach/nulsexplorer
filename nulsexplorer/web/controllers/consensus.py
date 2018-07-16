import aiohttp_jinja2
from nulsexplorer.model.consensus import Consensus
from nulsexplorer.web import app
from nulsexplorer.model.blocks import (Block, find_blocks, find_block,
                                       get_last_block_height)
from aiocache import cached, SimpleMemoryCache

@cached(ttl=60*10, cache=SimpleMemoryCache) # 600 seconds or 10 minutes
async def get_packer_stats(last_height):
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

    return (totals_all, totals_hour, totals_day)

@aiohttp_jinja2.template('consensus.html')
async def consensus(request):
    """ Address view
    """
    last_height = await get_last_block_height()
    consensus = await Consensus.collection.find_one(sort=[('height', -1)])

    #db.blocks.aggregate({$match: {'height': {'$gt': 40000}}},     )
    node_count = len(consensus['agents'])
    active_count = len([a for a in consensus['agents'] if a['status'] == 1])
    totals_all, totals_hour, totals_day = await get_packer_stats(last_height)

    return {'consensus': consensus,
            'last_height': last_height,
            'total_all': totals_all,
            'total_hour': totals_hour,
            'total_day': totals_day,
            'node_count': node_count,
            'active_count': active_count}
app.router.add_get('/consensus', consensus)
