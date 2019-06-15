from nulsexplorer.web import app
import aiohttp_jinja2
from nulsexplorer.model.blocks import Block, get_last_block_height
from nulsexplorer.model.consensus import Consensus
from aiocache import cached, SimpleMemoryCache
from statistics import mean

@cached(ttl=60*10, cache=SimpleMemoryCache) # 600 seconds or 10 minutes
async def calculate_ratio(qty=200):
    blocks = Block.collection.find().sort([('height',-1)]).limit(qty)
    consensus_items = Consensus.collection.find().sort([('height',-1)]).limit(qty)

    blocks = await blocks.to_list(length=qty)
    consensus_items = await consensus_items.to_list(length=qty)

    ratios = []

    for block, consensus_items in zip(blocks, consensus_items):
        agents = [agent for agent in consensus_items['agents']
                  if agent['packingAddress'] == block['packingAddress']]
        if not len(agents):
            continue
        agent = agents[0]
        if agent['creditVal'] < 0.96:
            continue # we got a too low score, will bork our calculation
        ratio = block['reward'] / (agent['totalDeposit']+agent['deposit'])
        ratios.append(ratio)

    return mean(ratios)

#@aiohttp_jinja2.template('calculator.html')
async def calculator(request):
    """Index of the block explorer.
    """
    ratio = await calculate_ratio()
    return {'ratio': ratio}

app.router.add_get('/tools/calculator', calculator)
