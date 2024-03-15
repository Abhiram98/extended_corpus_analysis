from pymongo import MongoClient
from prompt import  extract_method_messages, add_line_nums
import json

client = MongoClient('localhost', 27017)
db_name = 'extract_function'
collection_name = 'ef1_copy'
collection = client[db_name][collection_name]


data = []

# for obj in collection.find():
#     url = obj['host_function_before_ef']['url']
#     func_str = obj['host_function_before_ef']['function_src']
#     offset_line_num = int(url.split("#L")[1].split('-')[0]) -1
#
#     data.append({
#         "url":url,
#         "func_str": add_line_nums(func_str, offset=offset_line_num)
#     })
#
# with open("data/ef_data.json", 'w') as f:
#     json.dump(data, f, indent=1)





def transform_metadata(collection, key):
    for obj in collection.find():
        test_values = obj[key]
        for temp_value in list(test_values.keys()):
            if not temp_value.startswith("temperature"):
                del test_values[temp_value]
                continue
            if(isinstance(test_values[temp_value], dict)):
                print(obj['_id'])
                iter_keys = sorted(test_values[temp_value])
                [test_values[temp_value][i].update({"shot_no":int(i)}) for i in iter_keys]
                new_meta = [test_values[temp_value][i] for i in iter_keys]
                test_values[temp_value] = new_meta

        newvalues = {"$set": {key: test_values}}
        collection.update_one({'_id': obj['_id']}, newvalues)


def clean_metadata(collection, key):
    for obj in collection.find():
        test_values = obj[key]
        for temp_value in list(test_values.keys()):
            tval_str = temp_value
            if temp_value == 'temperature_1' or temp_value == 'temperature_0':
                print("found non-float", temp_value)
                tval = float(temp_value.split('_')[1])
                tval_str = f"temperature_{tval}"
                test_values[tval_str] = test_values[temp_value]
                del test_values[temp_value]
            elif len(temp_value) > 17:
                print("Bad temp value", temp_value)
                del test_values[temp_value]
                tval_str = None
            # if tval_str:
            #     # [i.update({"llm_processing_time":float(i['llm_processing_time'])})
            #      for i in test_values[tval_str]]
        newvalues = {"$set": {key: test_values}}
        collection.update_one({'_id': obj['_id']}, newvalues)


# collection.aggregate([{"$out": "ef1_copy"}])
transform_metadata(collection, 'multishot-gpt-3')
clean_metadata(collection, 'multishot-gpt-3')