from pymongo import MongoClient
from bson.objectid import ObjectId
from prompt import  extract_method_messages, add_line_nums
import json

client = MongoClient('localhost', 27017)
db_name = 'extract_function'
collection_name = 'ef1'
collection = client[db_name][collection_name]

my_path = '/Users/abhiram/Documents/JetGPT'
# myquery = { "address": "Valley 345" }
# newvalues = { "$set": { "address": "Canyon 123" } }
#
# mycol.update_one(myquery, newvalues)

for obj in collection.find():
    keys = [
        "local_filename",
        "local_path",
        "oracle.filename"
    ]

    filename = obj["local_filename"]

    relpath = filename.split('ef_xu_oracle/projects/')[1]

    new_filename = f"{my_path}/ef_xu_oracle/projects/{relpath}"
    newvalues = {"$set": {"local_filename": new_filename}}
    collection.update_one({'_id': obj['_id']}, newvalues)

    old_oracle = obj['oracle']
    old_oracle['filename'] = new_filename
    newvalues = {"$set": {"oracle": old_oracle}}
    collection.update_one({'_id': obj['_id']}, newvalues)



    ###
    local_path = obj["local_path"]
    relpath = local_path.split('ef_xu_oracle/projects/')[1]

    new_local_path = f"{my_path}/ef_xu_oracle/projects/{relpath}"
    newvalues = {"$set": {"local_path": new_local_path}}
    collection.update_one({'_id': obj['_id']}, newvalues)




    # break

