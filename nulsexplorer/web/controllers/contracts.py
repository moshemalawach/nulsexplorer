
from nulsexplorer.web import app
from nulsexplorer.model.transactions import Transaction
from nulsexplorer.model.blocks import (get_last_block_height)

from .utils import (Pagination, PER_PAGE, PER_PAGE_SUMMARY,
                    cond_output)

# async def get_contracts():
#     aggregate = Transaction.collection.aggregate([
#          {'$match': {'$and':
#             {'type': 100,
#              'info.result.success': True}}},
#          {'$sort': {'_id': 1}}])
#     return [item async for item in aggregate]

async def contracts_list(request):
    """ Contracts view
    """
    from nulsexplorer.model import db
    last_height = await get_last_block_height()
    page = int(request.match_info.get('page', '1'))

    contracts_query = {
        'type': 100,
        'info.result.success': True
    }
    total_contracts = await Transaction.collection.count(contracts_query)
    pagination = Pagination(page, PER_PAGE_SUMMARY, total_contracts)

    contract_creations = Transaction.collection.find(contracts_query,
                                                     sort=[('blockHeight', -1)],
                                                     skip=(page-1)*PER_PAGE_SUMMARY,
                                                     limit=PER_PAGE_SUMMARY)

    page = int(request.match_info.get('page', '1'))
    contract_creations = [tx async for tx in contract_creations]

    context = {'contract_creations': contract_creations,
               'pagination': pagination,
               'last_height': last_height,
               'pagination_page': page,
               'pagination_total': total_contracts,
               'pagination_per_page': PER_PAGE_SUMMARY,
               'pagination_item': 'contract_creations'}

    return cond_output(request, context, 'contracts.html')

app.router.add_get('/addresses/contracts', contracts_list)
app.router.add_get('/addresses/contracts.json', contracts_list)
app.router.add_get('/addresses/contracts/page/{page}', contracts_list)
app.router.add_get('/addresses/contracts/page/{page}.json', contracts_list)

async def view_contract(request):
    from .addresses import (addresses_unspent_info, summarize_tx)

    last_height = await get_last_block_height()

    address = request.match_info['address']
    mode = request.match_info.get('mode', 'summary')
    create_tx = await Transaction.collection.find_one({
        'type': 100,
        'info.contractAddress': address
    })

    if create_tx is None:
        raise web.HTTPNotFound(text="Contract not found")

    page = int(request.match_info.get('page', '1'))
    per_page = PER_PAGE_SUMMARY

    where_query = {'$or':
                    [{'info.contractAddress': address},
                     {'outputs.address': address},
                     {'inputs.address': address}]}
    tx_count = await Transaction.count(where_query)
    transactions = [tx async for tx in
                    Transaction.collection.find(where_query,
                                                sort=[('time', -1)],
                                                limit=per_page,
                                                skip=(page-1)*per_page)]

    unspent_info = (await addresses_unspent_info(last_height,
                                                 address_list=[address])
                    ).get(address, {})

    transactions = [await summarize_tx(tx, address) for tx in transactions]

    pagination = Pagination(page, per_page, tx_count)


    context = {'address': address,
               'create_tx': create_tx,
               'transactions': transactions,
               'pagination': pagination,
               'last_height': last_height,
               'tx_count': tx_count,
               'mode': mode,
               'pagination_page': page,
               'pagination_total': tx_count,
               'pagination_per_page': per_page,
               'pagination_item': 'transactions',
               'unspent_info': unspent_info}

    return cond_output(request, context, 'contract.html')

app.router.add_get('/addresses/contracts/{address}', view_contract)
app.router.add_get('/addresses/contracts/{address}/{mode}.json', view_contract)
app.router.add_get('/addresses/contracts/{address}/{mode}', view_contract)
app.router.add_get('/addresses/contracts/{address}/page/{page}.json', view_contract)
app.router.add_get('/addresses/contracts/{address}/page/{page}', view_contract)
app.router.add_get('/addresses/contracts/{address}/{mode}/page/{page}.json', view_contract)
app.router.add_get('/addresses/contracts/{address}/{mode}/page/{page}', view_contract)
