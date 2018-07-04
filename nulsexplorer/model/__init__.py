from logging import getLogger

log = getLogger(__name__)

import pymongo
try:
    from pymongo import MongoClient
except ImportError:  # pragma: no cover
    # Backward compatibility with PyMongo 2.2
    from pymongo import Connection as MongoClient

from motor.motor_asyncio import AsyncIOMotorClient

from nulsexplorer.web import app

db_backend = None

# Mongodb connection and db
connection = None
db = None


def init_db(ensure_indexes=True):
    global connection, db
    connection = AsyncIOMotorClient(app['config'].mongodb.uri.value,
                                    tz_aware=True)
    db = connection[app['config'].mongodb.database.value]
    sync_connection = MongoClient(app['config'].mongodb.uri.value,
                                    tz_aware=True)
    sync_db = sync_connection[app['config'].mongodb.database.value]

    if ensure_indexes:
        # do indexes if needed here...
        #from nulsexplorer.model.blocks import ensure_indexes
        #ensure_indexes(sync_db)
        from nulsexplorer.model.transactions import Transaction
        from nulsexplorer.model.blocks import Block
        Block.ensure_indexes(sync_db)
        Transaction.ensure_indexes(sync_db)
