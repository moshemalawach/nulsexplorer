""" Transactions are derived from Blocks txList.

To recreate (raw mongo, should be adapted for motor):
db.blocks.aggregate([ {$unwind: "$txList"}, {$replaceRoot: { newRoot: "$txList" }}, {$out: "transactions"}])
"""

import pymongo
from nulsexplorer.model.base import BaseClass, Index

import logging
LOGGER = logging.getLogger('model.transactions')

class Transaction(BaseClass):
    COLLECTION = "transactions"

    INDEXES = [Index("hash", unique=True),
               Index("blockHeight", pymongo.ASCENDING),
               Index("blockHeight", pymongo.DESCENDING),
               Index("time", pymongo.DESCENDING),
               Index("outputs.address"),
               Index("inputs.address")]

    @classmethod
    async def input_txdata(cls, tx_data):
        #await cls.collection.insert(tx_data)
        transaction = tx_data
        for i, inputdata in enumerate(transaction['inputs']):
            fidx = inputdata['fromIndex']
            source_tx = await cls.collection.find_one_and_update(
                dict(hash=inputdata['fromHash']),
                {'$set': {
                    ('outputs.%d.status' % fidx): 3,
                    ('outputs.%d.toHash' % fidx): transaction['hash'],
                    ('outputs.%d.toIndex' % fidx): i
                }})
            # if source_tx is not None:
            #     in_from = source_tx.outputs[inputdata['fromIndex']]
            #     inputdata['address'] = in_from['address']
            #     in_from['status'] = 3
            #     in_from['toHash'] = transaction.hash
            #     in_from['toIndex'] = i
            #     await source_tx.save()

        for outputdata in transaction['outputs']:
            if 'status' not in outputdata:
                if outputdata.get("lockTime", -1) > -1:
                    outputdata['status'] = 3 # how to know between 2 and 3 ?
                else:
                    outputdata['status'] = 0
        try:
            await cls.collection.insert_one(tx_data)
        except pymongo.errors.DuplicateKeyError:
            LOGGER.waning("Transaction %s was already there" % transaction['hash'])
