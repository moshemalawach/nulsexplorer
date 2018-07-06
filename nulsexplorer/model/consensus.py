
import pymongo
from nulsexplorer.model.base import BaseClass, Index

class Consensus(BaseClass):
    COLLECTION = "consensus"
    INDEXES = [Index("height", pymongo.DESCENDING, unique=True)]

class Agent(BaseClass):
    COLLECTION = "agents"
    INDEXES = [Index("agentHash"),
               Index("agentId"),
               Index("packingAddress")]
