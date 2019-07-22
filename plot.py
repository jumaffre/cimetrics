import yaml
from pymongo import MongoClient
import os

def get_settings():
  with open('metrics.yml') as cfgf:
    cfg = yaml.safe_load(cfgf)
    return cfg['db'], cfg['collection'], cfg['main_branch']

DB, COLLECTION, MAIN_BRANCH = get_settings()

if __name__ == '__main__':
  uri = os.getenv("COSMOS_CONNECTION")
  mongo_client = MongoClient(uri)
 
  db = mongo_client[DB]
  col = db[COLLECTION]
  docs = col.find({})
 
  for doc in docs:
    print(doc)
