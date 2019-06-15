from nulsexplorer.web import app
from nulsexplorer.model.consensus import Consensus
from nulsexplorer.model.transactions import Transaction
from .utils import cond_output
from nulsexplorer.web.controllers.tools import calculate_ratio
from aiocache import cached, SimpleMemoryCache

async def view_staking_rewards(request):
    """ Staking view
    """

    staked_amount = float(float(request.query.get('staked_amount', 2000)))

    consensus = await Consensus.collection.find_one(sort=[('height', -1)])
    consensus_size = len([a for a in consensus['agents'] if a['status'] == 1])
    staking_ratio = await calculate_ratio()

    per_nuls = staking_ratio * 0.9
    per_block = staked_amount * per_nuls
    per_day = (per_block * 6 * 60 * 24) / (consensus_size+3)
    per_month = per_day * 30
    per_year = per_day * 365

    context = {
      'per_nuls': per_nuls,
      'per_block': per_block,
      'per_day': per_day,
      'per_month': per_month,
      'per_year': per_year
    }

    return cond_output(request, context, '')

app.router.add_get('/staking/rewards.json', view_staking_rewards)

@cached(ttl=60*10, cache=SimpleMemoryCache) # 600 seconds or 10 minutes
async def get_all_deposits_txs():
    """ Returns the number of all stakers and the amount staked by each one
    """
    all_txs = Transaction.collection.find({
      'type': 5, # join consensus
      'outputs.status': {'$lt': 3},
      'outputs.lockTime': -1
    }, projection={
      'outputs.status': 1,
      'outputs.value': 1,
      'outputs.lockTime': 1,
      'outputs.address': 1
    })

    count = 0
    stakers = {}

    async for tx in all_txs:
        for output in tx['outputs']:
            lock_time = output['lockTime']
            address = output['address'] 
            value = output['value']

            if output['status'] >= 3:
                continue  # spent

            if lock_time != -1:
                continue  # not consensus locked

            if value < 200000000000: # minimum staking amount
                raise ValueError("Consensus deposit with less than 2k")
                continue  # something went wrong

            if stakers.get(address, None) is None:
              count += 1
              stakers[address] = 0
            
            stakers[address] += (value / 10**8)

    return  {
      'count': count,
      'stakers': stakers
    }

async def view_stakers_list(request):
    """ Returns the number of stakers who has currently staked more than `min_staked_amount` nuls in total in diferent nodes.
    """
    min_staked_amount = float(request.query.get('min_staked_amount', 2000))

    context = await get_all_deposits_txs()
    stakers = context.get('stakers', {})
    count = context.get('count', 0)

    filtered_stakers = {}
    filtered_count = 0

    for k, v in stakers.items():
        if v >= min_staked_amount:
          filtered_count += 1
          filtered_stakers[k] = v

    context = {
      'count': filtered_count,
      'stakers': filtered_stakers
    }

    return cond_output(request, context, '')
                                 
app.router.add_get('/staking/stakers.json', view_stakers_list)
