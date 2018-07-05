""" Transactions are derived from Blocks txList.

To recreate (raw mongo, should be adapted for motor):
db.blocks.aggregate([ {$unwind: "$txList"}, {$replaceRoot: { newRoot: "$txList" }}, {$out: "transactions"}])
"""

import pymongo
from nulsexplorer.model.base import BaseClass, Index

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
        transaction = cls(tx_data)
        for i, inputdata in enumerate(transaction['inputs']):
            source_tx = await cls.find_one(hash=inputdata['fromHash'])
            if source_tx is not None:
                in_from = source_tx.outputs[inputdata['fromIndex']]
                inputdata['address'] = in_from['address']
                in_from['status'] = 3
                in_from['toHash'] = transaction.hash
                in_from['toIndex'] = i
                await source_tx.save()

        for outputdata in transaction['outputs']:
            if 'status' not in outputdata:
                if outputdata.get("lockTime", -1) > -1:
                    outputdata['status'] = 3 # how to know between 2 and 3 ?
                else:
                    outputdata['status'] = 0

        await transaction.save()
