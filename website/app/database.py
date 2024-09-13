import pymongo

from settings import DBNAME, DBURL


client = pymongo.MongoClient(DBURL)
db = client[DBNAME]