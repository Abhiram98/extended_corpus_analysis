import re
import bson
import json
import pandas as pd
from bson.objectid import ObjectId

from mongo_manager import MongoManager

ALL_TEMPS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]


def move_under_temperature(db_str, temperature):
    mm = MongoManager.from_string(db_str)
    docs = mm.fetch_documents()

    temperature_key = f"temperature_{temperature}"
    llm_multishot_data_key = "llm_multishot_data"
    for doc in docs:
        if llm_multishot_data_key in doc:
            if temperature_key not in doc[llm_multishot_data_key]:
                multishot_data_array = [x for x in doc[llm_multishot_data_key]]
                doc.pop(llm_multishot_data_key)
                doc[llm_multishot_data_key] = {
                    temperature_key: multishot_data_array
                }
        mm.collection().update_one({"_id": doc["_id"]}, {"$set": doc})


def export_datase_for_rems(db_str):
    output_file = 'xu_dataset_for_rems.csv'
    csv_data = []
    mm = MongoManager.from_string(db_str)
    docs = mm.collection().find({"llm_multishot_data": {"$exists": True}})
    for doc in docs:
        csv_data.append(f'{doc["_id"]},{doc["local_filename"]},{doc["function_name"]}')
    with open(output_file, 'w') as ofile:
        ofile.write('\n'.join(csv_data))


def _find_intervals(line_list):
    intervals = []

    if not line_list:
        return intervals

    start = line_list[0]
    end = line_list[0]

    for num in line_list[1:]:
        if num == end + 1:
            end = num
        else:
            intervals.append([start, end])
            start = end = num

    intervals.append([start, end])  # Add the last interval

    return intervals


def _read_rems_results_file(filename):
    with open(filename, 'r') as ifile:
        data = ifile.readlines()
    data = list(filter(lambda
                           x: 'Testing data : ' in x or 'Recommending extracting code lines' in x or 'recommendation result of method' in x,
                       data))
    result = []
    for i in range(0, len(data), 3):
        class_name = data[i].replace('Testing data : ', '').strip()
        function_name = data[i + 1].replace('gecs recommendation result of method ', '').strip().split(' ')[0]
        suggestion_lines = data[i + 2].strip().replace('Recommending extracting code lines:', '')
        if suggestion_lines:
            suggestion_lines = [int(x) for x in suggestion_lines.split(',')]
            suggestion_lines = _find_intervals(suggestion_lines)
            # build intervals
        else:
            suggestion_lines = []
        result.append((class_name, function_name, suggestion_lines))

    return result


def build_rems_response(db_str):
    input_filename = '/Users/dpomian/hardwork/research/evaluation/rems/rems_results.txt'
    rems_result_data = _read_rems_results_file(input_filename)
    mm = MongoManager.from_string(db_str)
    docs = mm.collection().find({"llm_multishot_data": {"$exists": True}})
    # docs = mm.collection().find({"_id": bson.ObjectId("64dcf140783ce5ad5826e5b1")})

    idx = 0
    for doc in docs:
        oracle_src_filename = doc["local_filename"]
        oracle_function_name = doc["function_name"]
        rems_class_name, rems_function_name, rems_suggestion_lines = rems_result_data[idx]
        rems_url = doc["host_function_before_ef"]["url"]
        line_range_pattern = r"#L\d+-L\d+"
        if rems_class_name not in oracle_src_filename or rems_function_name != oracle_function_name:
            raise Exception(f"rems data not found for docId: {doc['_id']}")

        rems_suggestion_line_start = 1
        rems_suggestion_line_end = 1

        rems_ranking_doc = []
        for rems_line_range in rems_suggestion_lines:
            rems_suggestion_line_start, rems_suggestion_line_end = rems_line_range[0], rems_line_range[1]
            rems_suggestion_length = rems_suggestion_line_end - rems_suggestion_line_start + 1
            rems_url = f"{rems_url.split('#')[0]}#L{rems_suggestion_line_start}-L{rems_suggestion_line_end}"

            rems_candidate_doc = {
                "function_name": rems_function_name,
                "line_start": rems_suggestion_line_start,
                "line_end": rems_suggestion_line_end,
                "length": rems_suggestion_length,
                "url": rems_url
            }
            rems_ranking_doc.append(rems_candidate_doc)
        rems_ranking_doc = sorted(rems_ranking_doc, key=lambda x: x['length'], reverse=True)

        doc["rems_analysis"] = {"rank_by_size": rems_ranking_doc}
        mm.collection().update_one({"_id": doc["_id"]}, {"$set": doc})

        idx += 1


def _calculate_offby(oracle_ls_le, other_ls_le):
    oracle_ls, oracle_le = oracle_ls_le
    other_ls, other_le = other_ls_le
    offby = abs(int(oracle_ls) - int(other_ls)) + abs(int(oracle_le) - int(other_le))
    offby_s = int(oracle_ls) - int(other_ls)
    offby_e = int(other_le) - int(oracle_le)
    return offby, offby_s, offby_e


def find_large_candidates(db_str):
    mm = MongoManager.from_string(db_str)
    docs = mm.collection().find({"jetgpt_ranking": {"$exists": True}})

    percentages = {}
    for doc in docs:
        oracle_doc = doc["oracle"]
        oracle_hf_body_loc = int(oracle_doc["hf_body_loc"])
        oracle_ls = int(oracle_doc["line_start"])
        oracle_le = int(oracle_doc["line_end"])
        candidates = doc["jetgpt_ranking"]["multishot"]["temperature_1.0"]["rank_by_heat"]

        if len(candidates) > 0:
            for candidate in candidates:
                candidate_ls = candidate["line_start"]
                candidate_le = candidate["line_end"]
                offby, offby_start, offby_end = _calculate_offby((oracle_ls, oracle_le), (candidate_ls, candidate_le))
                candidate["offby"] = offby
                candidate["offby_start"] = offby_start
                candidate["offby_end"] = offby_end

            best_candidate = min(candidates, key=lambda obj: obj["offby"])
            bc_size = int(best_candidate["line_end"]) - int(best_candidate["line_start"]) + 1
            pc = bc_size / oracle_hf_body_loc
            percentages[str(doc["_id"])] = pc

    print('\n'.join([str(pc) for pc in percentages.values()]))
    print(f'max: {max(percentages.values())}')


def find_large_oracle(db_str):
    mm = MongoManager.from_string(db_str)
    docs = mm.collection().find({
        "oracle.loc": {"$gt": 1},
        "$expr": {"$gt": ["$oracle.hf_body_loc", "$oracle.loc"]},
    })

    count = 0
    csvs = ['doc_id,url,hf_body_loc,ef_loc,ratio']
    for doc in docs:
        doc_id = str(doc["_id"])
        oracle_doc = doc["oracle"]
        oracle_hf_body_loc = int(oracle_doc["hf_body_loc"])
        oracle_loc = int(oracle_doc["loc"])
        oracle_url = oracle_doc["url"]
        if oracle_hf_body_loc < 20 or oracle_hf_body_loc > 30:
            continue
        ratio = oracle_loc / oracle_hf_body_loc
        csvs.append(f'{doc_id},{oracle_url},{oracle_hf_body_loc},{oracle_loc},{ratio}')

    with open('icje_oracle_ratios.csv', 'w') as ofile:
        for csv in csvs:
            ofile.write(f'{csv}\n')

    mm.close()


def chatgpt_suggestions_evaluation(db_str, csv_filename, model, write=False, do_processing=True):
    temperature = 1.0
    # for temperature in ALL_TEMPS:

    evaluation_key = f"suggestion_evaluation_{model}"
    mm = MongoManager.from_string(db_str)
    docs = list(mm.collection().find({
        evaluation_key: {"$exists": True},
    }))

    csvs = []
    columns = ['doc_id', 'url', 'type', 'result', 'reason', 'temperature', 'line_start', 'line_end']
    print(model)
    print(f"{len(docs)=}")
    for temperature in ALL_TEMPS:
        str_temp = str(temperature).replace('.', '_')
        temperature_key = f'temperature_{str_temp}'

        for doc in docs:
            doc_id = str(doc["_id"])
            print(f'processing document: {doc_id}')

            candidates_with_application_result = doc[evaluation_key][temperature_key]
            for candidate in candidates_with_application_result:
                candiate_url = candidate["github_url"]
                result = candidate["application_result"]
                reason = candidate["application_reason"]
                candidate_type = candidate["candidate_type"]
                line_start = candidate['line_start']
                line_end = candidate['line_end']

                csvs.append((doc_id, candiate_url, candidate_type, result, reason, str(temperature), line_start, line_end))

    df = pd.DataFrame(csvs, columns=columns)
    print(f"{df.shape=}")

    df = df[df['type'] != 'ADJUSTED']
    if do_processing:
        df['all_temps'] = df.groupby(['doc_id','line_start','line_end'])\
            ["temperature"].transform(lambda x: ", ".join([str(i) for i in x]))

        df = df.drop_duplicates(['doc_id', 'line_start', 'line_end'], keep='last')

        df['line_count'] = df['line_end'] - df['line_start'] + 1
    if write:
        print("Writing df to csv")
        df.to_csv(csv_filename, index=False)


    print(f"{df.shape=}")
    correct_num = len(df[df['result']=='OK'])
    print("correct: ", correct_num)
    print("incorrect: ", len(df) - correct_num)
    # print("one liner functions", len(df['reason']))

    return df


def find_iter(docs, obj_id, temp,
              line_start, line_end, model):
    obj = [i for i in docs if i['_id']==ObjectId(obj_id)]
    assert  len(obj) == 1
    obj = obj[0]

    iter_val = -1
    for i, it_obj in enumerate(obj[f"multishot-{model}"][f"temperature_{temp}"]):
        if (line_start, line_end) in eval(it_obj['all-choices']):
            iter_val = i + 1
            break

    # if iter_val ==-1:
    #     raise Exception(f"{line_start, line_end} nor found in {obj_id}, temp:{temp}" )
    return iter_val

def add_iter_data(df, db_str, model):
    evaluation_key = f"suggestion_evaluation_{model}"
    mm = MongoManager.from_string(db_str)
    docs = list(mm.collection().find({
        evaluation_key: {"$exists": True},
    }))

    # df.groupby('temperature')

    iter_vals = []
    for index, row in df.iterrows():
        # print(row)
        obj_id = row['doc_id']
        temp = row['temperature']
        line_start = row['line_start']
        line_end = row['line_end']
        i = find_iter(docs, obj_id, temp,
                         line_start, line_end, model)
        # if i >0:
        iter_vals.append(i)
        # for suggestion in obj[evaluation_key]:
    df['iteration'] = iter_vals


def _read_json(json_filename):
    with open(json_filename, 'r') as jsonfile:
        json_data = json.load(jsonfile)
    return json_data


def _filter_json(json_data, filter_str):
    filtered_json_data = []
    # print(f"found {len(json_data['commits'])} commits")
    for refactor_instance in json_data['commits']:
        filtered_refactorings = list(filter(lambda x: x['type'] == filter_str, refactor_instance['refactorings']))
        if len(filtered_refactorings) > 0:
            refactor_instance['refactorings'] = filtered_refactorings
            filtered_json_data.append(refactor_instance)
    return filtered_json_data


def _get_method_and_class_name(description):
    method_name, class_name = '', ''
    if 'extracted from' in description:
        description = description[description.find('extracted from') + len('extracted from'):].strip()

        desc_tokens = description.split('in class')
        mn_tokens = desc_tokens[0].strip().split(' ')

        mnt = mn_tokens[1] if len(mn_tokens) > 1 else mn_tokens[0]
        method_name = mnt[:mnt.find('(')]
        class_name = desc_tokens[1].strip().split('.')[-1]
    return method_name, class_name


def enrich_with_method_name_and_class_name(db_str, json_file):
    mm = MongoManager.from_string(db_str)
    docs = mm.collection().find()

    json_data = _read_json(json_file)
    json_data = _filter_json(json_data, 'Extract Method')

    for doc in docs:
        doc_id = str(doc["_id"])
        print(f'processing document: {doc_id}')

        hf_url = doc['host_function_before_ef']['url']
        hf_line_start, hf_line_end = hf_url.split('#')[1].replace('L', '').split('-')
        hf_line_start = int(hf_line_start)
        hf_line_end = int(hf_line_end)
        hf_file_name = doc['host_function_before_ef']['filename']

        json_records = list(filter(lambda x: x['sha1'] == doc['sha_ef'], json_data))
        found = False
        for jrecord in json_records:
            jrecord_refactorings = jrecord['refactorings']
            for jrecord_refactoring in jrecord_refactorings:
                left_side_locations = list(filter(
                    lambda x: int(x['startLine']) == hf_line_start and int(x['endLine']) == hf_line_end and x[
                        'filePath'] == hf_file_name, jrecord_refactoring['leftSideLocations']))
                if left_side_locations:
                    description = jrecord_refactoring['description']
                    method_name, class_name = _get_method_and_class_name(description)
                    if method_name and class_name:
                        found = True
                        break
            if found:
                break
        if found:
            doc['function_name'] = method_name
            doc['class_name'] = class_name
            mm.collection().update_one({"_id": doc["_id"]}, {"$set": doc})

    mm.close()


if __name__ == '__main__':
    # move_under_temperature('ef_evaluation/revisited_xu_dataset', 0.0)
    # export_datase_for_rems('ef_evaluation/revisited_xu_dataset')
    # build_rems_response('ef_evaluation/revisited_xu_dataset')
    # find_large_candidates('ef_evaluation/revisited_xu_dataset')
    # find_large_oracle('playground_refminer/ijce')
    # chatgpt_suggestions_evaluation('ef_evaluation/revisited_xu_dataset', 'xu_dataset_chatgpt_evaluation.csv')
    # chatgpt_suggestions_evaluation('playground_refminer/ijce', 'ijce_chatgpt_evaluation.csv')
    # chatgpt_suggestions_evaluation('RefactoringMiner/CoreNLP_dataset', 'corenlp_chatgpt_evaluation.csv')
    # chatgpt_suggestions_evaluation('RefactoringMiner/SilvaDataset', 'silva_dataset_chatgpt_evaluation.csv')
    # enrich_with_method_name_and_class_name('playground_refminer/ijce', '/Users/dpomian/hardwork/research/TsantalisRefactoringMiner/build/distributions/RefactoringMiner-2.4.0/bin/jb__intellij_community_2.json')
    # enrich_with_method_name_and_class_name('RefactoringMiner/CoreNLP_dataset', '/Users/dpomian/hardwork/research/TsantalisRefactoringMiner/build/distributions/RefactoringMiner-2.4.0/bin/corenlp.json')

    # df_gpt_3 = chatgpt_suggestions_evaluation('extract_function/ef1_copy', 'xu_dataset_evaluation_gpt_3.csv',
    #                                           model='gpt-3', write=False)

    df_gpt_4 = chatgpt_suggestions_evaluation('extract_function/ef1_gpt_4', 'xu_dataset_evaluation_gpt_4.csv',
                                              model='gpt-4', write=True)
    # df_palm = chatgpt_suggestions_evaluation('extract_function/ef1_copy', 'xu_dataset_evaluation_palm.csv',
    #                                          model='palm', write=False)
