from nulsexplorer import model

async def get_address_aggregates(address_list=None, key_list=None):
    aggregate = [
        {'$match': {
            'info.type': 'ipfs',
            'info.aggregate':  { '$exists': True }
        }},
        {'$addFields': {
            'first_input': {'$arrayElemAt': ['$inputs', 0]}
        }},
        {'$group':{
            '_id': {
                'address': '$first_input.address',
                'key': '$info.aggregate.key'
                },
            'content': {
                '$mergeObjects': '$info.aggregate.content'
            }
        }},
        {'$group': {
            '_id': '$_id.address',
            'items': {
                '$push': {
                    'k': '$_id.key',
                    'v': '$content'
                }
            }
        }},
        {'$addFields': {
            'address': '$_id',
            'contents': {
                '$arrayToObject': '$items'
            }
        }},
        {'$project': {
            '_id': 0,
            'address': 1,
            'contents': 1
        }}
    ]
    if address_list is not None:
        aggregate[0]['$match']['inputs.address'] = {'$in': address_list}

    if key_list is not None:
        aggregate[0]['$match']['info.aggregate.key'] = {'$in': key_list}

    results = model.db.transactions.aggregate(aggregate)

    return {result['address']: result['contents']
            async for result in results}
