import pymongo
from nulsexplorer.model.base import BaseClass, Index

class Address(BaseClass):
    COLLECTION = "addresses"
    INDEXES = [Index("hash", unique=True)]
