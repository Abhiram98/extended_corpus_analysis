import itertools
import random
from pymongo import MongoClient
from collections import defaultdict
import copy
from datetime import datetime

def get_all_responses(db_str,
                      model='gpt-3',
                        temperature = 1.2,
                        iteration = 10):
    client = MongoClient('localhost', 27017)
    db_name, collection_name = db_str.split('/')
    collection = client[db_name][collection_name]

    passes = list(range(6))
    MAX_SAMPLES = 100



    query = collection.find({
        "$and": [
            {
                "llm_multishot_data": {
                    "$exists": True
                }
            },
        ]
    })
    all_objs = list(query)

    llm_responses = defaultdict(list)
    passes = list(range(6))

    for obj in all_objs:
        print(f"Sampling {obj['_id']}")
        for pass_no in passes:
            responses = obj[f'multishot-{model}-pass-{pass_no}'][f'temperature_{temperature}']
            llm_responses[obj['_id']] += [i for i in responses
                                        if not i['api_failed'] and not i['response_parse_failed']]
    return llm_responses


def get_samples(possible_responses, num_samples, sample_size):
    my_random = random.Random(42)
    return (my_random.sample(possible_responses, sample_size) for _ in range(num_samples))


def main():
    client = MongoClient('localhost', 27017)
    db_name = 'extract_function'
    # collection_name = 'ef1_stats_copy'
    collection_name = 'ef1_stats_resampling'
    collection = client[db_name][collection_name]

    passes = list(range(9))
    MAX_SAMPLES = 10

    model = 'gpt-3'
    temperature = 1.2
    iteration = 10

    query = collection.find({
        "$and": [
            {
                "llm_multishot_data": {
                    "$exists": True
                }
            },
        ]
    })
    all_objs = list(query)

    llm_responses = defaultdict(list)
    for obj in all_objs:
        print(f"Sampling {obj['_id']}")
        for pass_no in passes:
            responses = obj[f'multishot-{model}-pass-{pass_no}'][f'temperature_{temperature}']
            llm_responses[obj['_id']] += [i for i in responses
                                        if not i['api_failed'] and not i['response_parse_failed']]

        doc_id = obj['_id']
        for sample_no in range(MAX_SAMPLES):
            my_random = random.Random(datetime.now().timestamp())

            sample = copy.copy(my_random.sample(llm_responses[doc_id], iteration))
            for i, s in enumerate(sample):
                s["shot_no"] = i
            sample_key = f"multishot-{model}-sample-{sample_no}"
            sample_value = obj.get(sample_key, {})
            sample_value[f"temperature_{temperature}"] = sample
            newvalues = {"$set": {sample_key: sample_value}}
            collection.update_one({'_id': obj['_id']}, newvalues)





if __name__ == '__main__':
    main()