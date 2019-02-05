from nulsexplorer.modules.additional.ipfs import add_json, add_file
from nulsexplorer.modules.additional.account import get_address_aggregates
from nulsexplorer.model.blocks import (get_last_block_height)
from nulsexplorer.model.transactions import Transaction
from nulsexplorer.web import app

from aiohttp import web

async def ipfs_add_json(request):
    """ Forward the json content to IPFS server and return an hash
    """
    data = await request.json()

    output = {
        'status': 'success',
        'hash': await add_json(data)
    }
    return web.json_response(output)

app.router.add_post('/ipfs/add_json', ipfs_add_json)

async def ipfs_add_file(request):
    post = await request.post()
    output = await add_file(post['file'].file, post['file'].filename)

    output = {
        'status': 'success',
        'hash': output['Hash'],
        'name': output['Name'],
        'size': output['Size']
    }
    return web.json_response(output)

app.router.add_post('/ipfs/add_file', ipfs_add_file)


async def address_aggregate(request):
    """ Forward the json content to IPFS server and return an hash
    """

    address = request.match_info['address']
    last_height = await get_last_block_height()
    aggregates = await get_address_aggregates(address_list=[address])

    output = {
        'last_height': last_height,
        'address': address,
        'data': aggregates.get(address, {})
    }
    return web.json_response(output)

app.router.add_get('/addresses/aggregates/{address}.json', address_aggregate)


async def view_posts_list(request):
    """ Transaction list view with filters
    """
    from nulsexplorer.web.controllers.utils import (Pagination, PER_PAGE,
                                                    cond_output, prepare_date_filters,
                                                    prepare_block_height_filters)

    find_filters = {}
    filters = [
        {'info.type': 'ipfs',
         'info.success': True,
         'info.post':  { '$exists': True }}
    ]

    query_string = request.query_string
    addresses = request.query.get('addresses', None)
    if addresses is not None:
        addresses = addresses.split(',')

    refs = request.query.get('refs', None)
    if refs is not None:
        refs = refs.split(',')

    post_types = request.query.get('types', None)
    if post_types is not None:
        post_types = post_types.split(',')

    tags = request.query.get('tags', None)
    if tags is not None:
        tags = tags.split(',')

    date_filters = prepare_date_filters(request, 'time')
    block_height_filters = prepare_block_height_filters(request, 'blockHeight')

    if addresses is not None:
        filters.append({
            'inputs.address': {'$in': addresses}
        })

    if post_types is not None:
        filters.append({'info.post.type': {'$in': post_types}})

    if refs is not None:
        filters.append({'info.post.ref': {'$in': refs}})

    if tags is not None:
        filters.append({'info.post.content.tags': {'$elemMatch': {'$in': tags}}})

    if date_filters is not None:
        filters.append(date_filters)

    if block_height_filters is not None:
        filters.append(block_height_filters)

    if len(filters) > 0:
        find_filters = {'$and': filters} if len(filters) > 1 else filters[0]

    pagination_page, pagination_per_page, pagination_skip = Pagination.get_pagination_params(request)
    if pagination_per_page is None:
        pagination_per_page = 0
    if pagination_skip is None:
        pagination_skip = 0

    transactions = [tx async for tx
                    in Transaction.collection.find(
                        find_filters, limit=pagination_per_page,
                        skip=pagination_skip, sort=[('blockHeight', -1)],
                        projection={
                            'hash': True,
                            'time': True,
                            'blockHeight': True,
                            'info': True,
                            'inputs': {'$slice': 1}
                        }
                    )]
    posts = [{
        'hash': tx['hash'],
        'address': tx['inputs'][0]['address'],
        'blockHeight': tx['blockHeight'],
        'time': tx['time'],
        **tx['info']['post']
    } for tx in transactions]

    context = {
        'posts': posts,
        'last_height': await get_last_block_height()
    }

    if pagination_per_page is not None:
        total_txs = await Transaction.count(find_filters)

        pagination = Pagination(pagination_page, pagination_per_page, total_txs,
                                url_base='/transactions/page/', query_string=query_string)

        context.update({
            'pagination': pagination,
            'pagination_page': pagination_page,
            'pagination_total': total_txs,
            'pagination_per_page': pagination_per_page,
            'pagination_item': 'posts'
        })

    return cond_output(request, context, 'TODO.html')

app.router.add_get('/ipfs/posts.json', view_posts_list)
app.router.add_get('/ipfs/posts/page/{page}.json', view_posts_list)
