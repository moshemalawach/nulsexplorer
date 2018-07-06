
import pymongo
from nulsexplorer.model.base import BaseClass, Index

class Address(BaseClass):
    COLLECTION = "transactions"
    INDEXES = [Index("hash", unique=True)]

    
