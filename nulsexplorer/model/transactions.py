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
               Index("outputs.address")]
