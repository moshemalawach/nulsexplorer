
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
    total_contracts = await  Transaction.collection.count(contracts_query)
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
              'pagination_item': 'addresses'}

    return cond_output(request, context, 'contracts.html')

app.router.add_get('/contracts', contracts_list)
app.router.add_get('/contracts.json', contracts_list)
app.router.add_get('/contracts/page/{page}', contracts_list)
app.router.add_get('/contracts/page/{page}.json', contracts_list)
