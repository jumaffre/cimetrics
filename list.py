from pymongo import MongoClient
import json
import os
 
uri = os.getenv("COSMOS_CONNECTION")
mongo_client = MongoClient(uri)
 
db = mongo_client["metrics"]
col = db["metrics"]
docs = col.find({})
 
for doc in docs:
  print(doc)
