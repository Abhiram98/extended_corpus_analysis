from pymongo import MongoClient

from em_writer import EMwriter


class MongoWriter(EMwriter):

    def __init__(self, mongo_str, dest_dir):
        self.client = MongoClient('localhost', 27017)
        self.db_name, self.collection_name = mongo_str.split('/')
        self.collection = self.client[self.db_name][self.collection_name]
        self.all_objs = list(self.collection.find({}))

        self.dest_dir = dest_dir

    def write(self, em_metadata, dest_file):
        pass

    def read(self, function_details):
        pass

    def getdata(self):
        return self.all_objs

    def get_filename(self, em_data):
        return em_data['oracle']['filename']

    def get_projectname(self, em_data):
        return em_data['host_function_before_ef']['url']\
                .split('github.com/')[1].split("/")[1]

    def get_commitafter(self, em_data):
        return em_data['sha_ef']

    def get_func_str(self, em_data, file_str):
        return em_data['host_function_before_ef']['function_src']

    def get_startline(self, em_data):
        return int(em_data['host_function_before_ef']['url']\
                .split('#L')[1].split('-')[0])

    def get_endline(self, em_data):
        return int(em_data['host_function_before_ef']['url'] \
                   .split('#L')[1].split('-')[1].lstrip('L'))


    def exists(self, dest_file):
        return False