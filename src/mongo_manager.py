import pymongo
from bson.objectid import ObjectId
from bson.errors import InvalidId


class MongoManager:
    def from_string(db_str):
        db_name, collection_name = db_str.split('/')
        return MongoManager(db_name, collection_name)

    def __init__(self, db_name, col_name):
        self._conn_str = 'mongodb://localhost:27017/'
        self._client = pymongo.MongoClient(self._conn_str)
        self._db = self._client[db_name]
        self._col = self._db[col_name]
        self._data = {}

    def collection(self):
        return self._col

    def persist(self, json_data):
        insert_result = self._col.insert_one(json_data)
        return insert_result

    def clear_collection(self):
        self._col.delete_many({})

    def fetch_documents(self, id=None):
        if id is not None:
            try:
                result = self._col.find_one({"_id": ObjectId(id)})
                return [result] if result is not None else []
            except InvalidId:
                return []
        return [doc for doc in self._col.find()]

    def close(self):
        self._client.close()
