import aiohttp_jinja2
from aiohttp import web
from aiocache import cached, SimpleMemoryCache
from nulsexplorer.model.consensus import Consensus
from nulsexplorer.web import app
from nulsexplorer.model.transactions import Transaction
from nulsexplorer.model.blocks import (Block, find_blocks, find_block,
                                       get_last_block_height)
from nulsexplorer.web.controllers.addresses import summarize_tx
from .utils import Pagination, PER_PAGE, PER_PAGE_SUMMARY, cond_output

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

@cached(ttl=60*10, cache=SimpleMemoryCache) # 600 seconds or 10 minutes
async def get_consensus_stats(last_height, periods=96):
    heights = list(reversed([last_height-(v*6*60) for v in range(periods)]))
    item_query = {'$group' : {
      '_id' : '$height',
      'totalDeposit' : {'$sum' : '$agents.totalDeposit'},
      'activeNodes': {'$sum': {'$cond': [
        {'$eq': ['$agents.status', 1]}, 1, 0
        ]}}
      }}

    values = Consensus.collection.aggregate([
        {'$match': {'height': {'$in': heights}}},
        #{'$match': {'height': {'$gte': last_height-(days*8640)}}},
        {'$unwind': '$agents'},
        item_query,
        {'$sort': {'_id': 1} }
        # {'$group':
        #     {
        #         '_id':
        #         {
        #             '$subtract': [
        #                 '$_id',
        #                 {'$mod': ['$_id', 8640]}
        #             ]
        #         },
        #         'height': {'$last': '$_id'},
        #         'totalDeposit': {'$avg': '$totalDeposit'},
        #         'activeNodes': {'$avg': '$activeNodes'}
        #     }
        # }
    ])

    return [v async for v in values]

@aiohttp_jinja2.template('consensus.html')
async def view_consensus(request):
    """ Address view
    """
    last_height = await get_last_block_height()
    consensus = await Consensus.collection.find_one(sort=[('height', -1)])

    #db.blocks.aggregate({$match: {'height': {'$gt': 40000}}},     )
    node_count = len(consensus['agents'])
    total_deposit = sum([a['totalDeposit'] for a in consensus['agents']])
    active_count = len([a for a in consensus['agents'] if a['status'] == 1])
    totals_all, totals_hour, totals_day = await get_packer_stats(last_height)

    stats = await get_consensus_stats(last_height)
    stats_heights = [s['_id'] for s in stats]
    stats_stacked_values = [int(s['totalDeposit']/100000000000) for s in stats] # in KNuls
    stats_active_nodes = [s['activeNodes'] for s in stats]
    context = {'consensus': consensus,
            'last_height': last_height,
            'total_all': totals_all,
            'total_hour': totals_hour,
            'total_day': totals_day,
            'node_count': node_count,
            'active_count': active_count,
            'total_deposit': total_deposit,
            'stats': stats,
            'stats_heights': stats_heights,
            'stats_stacked_values': stats_stacked_values,
            'stats_active_nodes': stats_active_nodes}

    return cond_output(request, context, 'consensus.html')

app.router.add_get('/consensus.json', view_consensus)
app.router.add_get('/consensus', view_consensus)

#@aiohttp_jinja2.template('node.html')
async def view_node(request):
    """ Node view
    """
    last_height = await get_last_block_height()
    txhash = request.match_info['hash']
    transaction = await Transaction.find_one(hash = txhash)
    if transaction is None:
        raise web.HTTPNotFound(text="Transaction not found")
    block = await find_block({'height': transaction['blockHeight']})
    consensus = await Consensus.collection.find_one(sort=[('height', -1)])

    agent = None
    if txhash in [a['agentHash'] for a in consensus['agents']]:
        agent = [a for a in consensus['agents'] if a['agentHash'] == txhash][0]

    mode = request.match_info.get('mode', 'summary')
    if mode not in ['stats', 'summary', 'cards-summary', 'detail']:
        raise web.HTTPNotFound(text="Display mode not found")
    per_page = PER_PAGE
    if "summary" in mode:
        per_page = PER_PAGE_SUMMARY

    page = int(request.match_info.get('page', '1'))
    if mode == 'cards-summary':
        where_query = {'$or':
                        [{'$and': [
                            {'type': 7}, # yellow card
                            {'info.addresses': transaction['info']['agentAddress']}
                         ]},
                         {'$and': [
                             {'type': 8}, # red card
                             {'info.address':  transaction['info']['agentAddress']}
                         ]}
                        ]}
    else:
        where_query = {'$or':
                        [{'$and': [
                            {'type': 9}, # unregister
                            {'info.createTxHash': txhash}
                         ]},
                         {'$and': [
                             {'type': 5}, # join
                             {'info.agentHash': txhash}
                         ]},
                         {'$and': [
                             {'type': 6}, # leave
                             {'info.agentHash': txhash}
                         ]},
                         {'$and': [
                             {'type': 4}, # register
                             {'hash': txhash}
                         ]},
                         {'$and': [
                             {'type': 3}, # register
                             {'inputs.address': transaction['info']['agentAddress']}
                         ]}]}
    tx_count = await Transaction.count(where_query)
    print(tx_count)

    transactions = [tx._data async for tx in Transaction.find(where_query,
                                                        sort='time',
                                                        sort_order=-1,
                                                        limit=per_page,
                                                        skip=(page-1)*per_page)]
    if "summary" in mode:
        transactions = [await summarize_tx(tx,
                                           transaction['info']['agentAddress'],
                                           node_mode=True)
                        for tx in transactions]

    pagination = Pagination(page, per_page, tx_count)

    context = {'agent': agent,
            'transaction': transaction._data,
            'block': block,
            'consensus': consensus,
            'transactions': transactions,
            'pagination': pagination,
            'last_height': last_height,
            'tx_count': tx_count,
            'mode': mode,
            'pagination_page': page,
            'pagination_total': tx_count,
            'pagination_per_page': per_page,
            'pagination_item': 'transactions'}

    return cond_output(request, context, 'node.html')

app.router.add_get('/consensus/node/{hash}.json', view_node)
app.router.add_get('/consensus/node/{hash}', view_node)
app.router.add_get('/consensus/node/{hash}/{mode}.json', view_node)
app.router.add_get('/consensus/node/{hash}/{mode}', view_node)
app.router.add_get('/consensus/node/{hash}/page/{page}.json', view_node)
app.router.add_get('/consensus/node/{hash}/page/{page}', view_node)
app.router.add_get('/consensus/node/{hash}/{mode}/page/{page}.json', view_node)
app.router.add_get('/consensus/node/{hash}/{mode}/page/{page}', view_node)
