from nulsexplorer import app
from aiohttp import web

async def get_global_stats():
    from nulsexplorer.model import db
    values = db.cached_unspent.aggregate([
        {'$group': {
            '_id': None,
            'unspent_value': {'$sum': '$unspent_value'},
            'available_value': {'$sum': '$available_value'},
            'locked_value': {'$sum': '$locked_value'},
            'consensus_locked_value': {'$sum': '$consensus_locked_value'},
            'time_locked_value': {'$sum': '$time_locked_value'},
            'addresses': {'$sum': 1}
        }}
    ])
    values = await values.__anext__()

    return values

async def supplytxt(request):
    """Index of the block explorer.
    """
    stats = await get_global_stats()
    val = stats['available_value'] + stats['locked_value']
    return web.Response(text="%0.2f" % (val/100000000))
app.router.add_get('/ledger/assets/nuls/supply.txt', supplytxt)

async def supply_info(request):
    """Index of the block explorer.
    """
    stats = await get_global_stats()
    del stats['_id']
    return web.json_response(stats)
app.router.add_get('/ledger/assets/nuls/supply_info.json', supply_info)
