import copy
import os
import pprint
from get_completion import get_completion_messages
import json
from pymongo import MongoClient
from bson.objectid import ObjectId
from prompt import extract_method_messages, add_line_nums
import json
import numpy as np
import click
import subprocess
import functools
import my_grazie

pp = pprint.PrettyPrinter(indent=2)


class EMIterator:
    def __init__(self, num_iterations):
        self.num_iterations = num_iterations
        self.iter_func = self._fixpoint_iter if self.num_iterations == 0 else self._llm_iter

    def iterate(self,  func_str, model, temperature):
        return self.iter_func(func_str, model, temperature)

    def _fixpoint_iter(self, func_str, model, temperature):
        MAX_CHANCES = 2
        metadata = []
        ef_choices = set()
        chances = MAX_CHANCES
        new_choices = True
        iteration = 0
        MAX_ITERS = 20

        while chances or new_choices:
            if iteration >= MAX_ITERS:
                break
            print(f"iteration-{iteration}")
            print("EF Options so far")
            pp.pprint(ef_choices)
            func_numbered = func_str
            messages = extract_method_messages(func_numbered)
            try:
                response, response_extracted, time_taken = my_grazie.query(model, temperature, messages)
                api_failed = False
            except Exception as e:
                print("Error", e)
                response, response_extracted, time_taken = '', '[]', 0
                api_failed = f"{type(e)}:{str(e)}"

            time_taken_ms = time_taken * 1000

            old_size = len(ef_choices)
            try:
                new_ef_choices = json.loads(response_extracted)
                parse_failed = False
            except json.JSONDecodeError:
                new_ef_choices = []
                parse_failed = True
                print("response parse failed.")

            if not isinstance(new_ef_choices, list):
                parse_failed = f"invalid-format:{json.dumps(new_ef_choices)}"
            else:
                for ef in new_ef_choices:
                    ls = ef.get('line_start')
                    le = ef.get('line_end')
                    if ls is None or le is None:
                        parse_failed = f"missing-keys:{json.dumps(new_ef_choices)}"
                        continue
                    ef_choices.add((ls, le))

            new_choices = len(ef_choices) > old_size
            if not new_choices:
                chances -= 1
                print(f"No new choices found. {chances} chance(s) left.")
            else:
                chances = MAX_CHANCES
                print("new ef choices found!")

            metadata.append({
                "llm_raw_response": json.dumps(response),
                "response_extracted": response_extracted,
                "new-choices": json.dumps(new_ef_choices),
                "all-choices": str(ef_choices),
                "llm_processing_time": time_taken_ms,
                "response_parse_failed": parse_failed,
                "api_failed": api_failed,
                "shot_no": iteration

            })
            iteration += 1

        return metadata

    def _llm_iter(self, func_str, model, temperature):
        metadata = []
        ef_choices = set()

        for iteration in range(self.num_iterations):
            # print(f"iteration-{iteration}")
            # print("EF Options so far")
            # pp.pprint(ef_choices)
            func_numbered = func_str
            messages = extract_method_messages(func_numbered)
            try:
                response, response_extracted, time_taken = my_grazie.query(model, temperature, messages)
                api_failed = False
            except Exception as e:
                print("Error", e)
                response, response_extracted, time_taken = '', '[]', 0
                api_failed = f"{type(e)}:{str(e)}"
                # iteration-=1
                # continue

            time_taken_ms = time_taken * 1000

            try:
                new_ef_choices = json.loads(response_extracted)
                parse_failed = False
            except json.JSONDecodeError:
                new_ef_choices = []
                parse_failed = True
                print("response parse failed.")

            if not isinstance(new_ef_choices, list):
                parse_failed = f"invalid-format:{json.dumps(new_ef_choices)}"
            else:
                for ef in new_ef_choices:
                    ls = ef.get('line_start')
                    le = ef.get('line_end')
                    if ls is None or le is None:
                        parse_failed = f"missing-keys:{json.dumps(new_ef_choices)}"
                        continue
                    ef_choices.add((ls, le))

            metadata.append({
                "llm_raw_response": json.dumps(response),
                "response_extracted": response_extracted,
                "new-choices": json.dumps(new_ef_choices),
                "all-choices": str(ef_choices),
                "llm_processing_time": time_taken_ms,
                "response_parse_failed": parse_failed,
                "api_failed": api_failed,
                "shot_no": iteration

            })

        return metadata


def fix_missing(all_objs, model='gpt-4'):
    api_failed_objs = []
    for obj in all_objs:
        for temp in TEMPS:
            for sub_obj in obj[f'multishot-{model}'][f"temperature_{temp}"]:
                if 'api_failed' in sub_obj and sub_obj['api_failed'] \
                        and 'openai.error.RateLimitError' in sub_obj['api_failed']:
                    print(obj['_id'], temp)
                    print(sub_obj['api_failed'])
                    # print(obj['multishot-gpt-3'][f"temperature_{temp}"])
                    api_failed_objs.append((obj, temp))
    completed = set()
    model_key = f"multishot-{model_alias.get(model, model)}"
    for obj, temp in api_failed_objs:
        print("completed set: ", len(completed), len(api_failed_objs))
        pp.pprint(completed)
        if ((obj['_id'], temp) in completed):
            print("already done")
            continue
        func_str = obj['host_function_before_ef']['function_src']
        func_str = func_str.replace('\\n', '\n')
        url = obj['host_function_before_ef']['url']
        offset_line_num = int(url.split("#L")[1].split('-')[0]) - 1

        fd = {
            "url": url,
            "func_str": add_line_nums(func_str, offset_line_num)
        }

        metadata = fixpoint_iter(fd, model=model, temperature=temp)

        val = obj.get(model_key, {})
        val[f"temperature_{temp}"] = metadata
        obj[model_key] = val
        newvalues = {"$set": {model_key: val}}
        collection.update_one({'_id': obj['_id']}, newvalues)
        completed.add((obj['_id'], temp))


def get_parent_commit(project_dir, commit_hash):
    # git log --pretty=%P -n 1 "<commit-hash>"
    response = subprocess.run([
        "git", "-C", f"{project_dir}",
        "log", "--pretty=%P",
        '-n', '1',
        commit_hash
    ], stdout=subprocess.PIPE)

    return response.stdout.decode('utf-8').strip()

def change_git(project_dir, commit_hash):
    subprocess.run([
        "git", "-C", f"{project_dir}",
        "restore", "."
    ])

    subprocess.run([
        "git", "-C", f"{project_dir}",
        "checkout", "-f", commit_hash
    ])


@click.command()
@click.option("--rminer_out_file", help="refactoring miner output in json format.")
@click.option("--project_name", help='name of project')
@click.option("--projects_dir", help='root directory containing project', default='../projects')
@click.option("--output_dir", help="destination to save LLM output to.", default='../data/em-assist')
@click.option("--llm_name", help='llm to query', default='gpt-4')
@click.option("--num_iterations", help='num of iterations to run LLM. If 0, run till fixpoint', default=15, type=int)
@click.option("--temp", help="temperature to run llm for. If -1, then run for all temperatures in (0,0.2, 0.4, 0.6, "
                             "0.8, 1.0, 1.2)", default=1.2, type=float)
def ask_llm(rminer_out_file, project_name,
            projects_dir, output_dir, llm_name, num_iterations,
            temp):
    with open(rminer_out_file) as f:
        rminer_data = json.load(f)

    em_iter = EMIterator(num_iterations)

    for i, em_data in enumerate(rminer_data):

        print(f"Completed {i}/{len(rminer_data)}")
        filename = em_data['filename']
        assert project_name == em_data['projectName'].split('/')[-1]

        project_path = f"{projects_dir}/{project_name}"
        commit_hash = em_data['sha']
        parent_hash = get_parent_commit(project_path, commit_hash)
        change_git(project_path, parent_hash)

        with open(f"{projects_dir}/{project_name}/{filename}") as f:
            file_str = f.read()

        start_offset = em_data['host_start_off_set']
        end_offset = em_data['host_end_off_set']
        func_str = file_str[start_offset:end_offset]
        print()

        start_line = em_data['host_start_line']
        end_line = em_data['host_end_line']
        func_str_with_line_nums = add_line_nums(func_str, start_line - 1)

        dest_dir = f"{output_dir}/{llm_name}/temp-{temp}/{project_name}"
        dest_file = f"{dest_dir}/func-{i}.json"

        if not os.path.exists(dest_file):
            results = em_iter.iterate(func_str_with_line_nums, model=llm_name, temperature=temp)
            try:
                os.makedirs(dest_dir)
            except FileExistsError:
                pass
            with open(dest_file, "w") as f:
                json.dump(results, f, indent=1)

if __name__ == '__main__':
    ask_llm(["--rminer_out_file",
             '../data/rminer/code-disaster_steamworks4j.json',
             '--project_name', 'steamworks4j',
             '--temp', '1.2'],
            standalone_mode=False)

    # models = [
    #     # 'gpt-4',
    #     'gpt-3.5-turbo',
    #     # 'palm'
    # ]
    # model_alias = {
    #     'gpt-3.5-turbo': 'gpt-3'
    # }
    # # TEMPS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2]
    # TEMPS = [1.2]
    # total_passes = 50
    # for PASS in range(total_passes):
    #     print(f"Pass: {PASS}")
    #     for model in models:
    #         for obji, obj in enumerate(all_objs):
    #             print("Working on ", obj['_id'])
    #             print(f"{obji}/{len(all_objs)} completed.")
    #             for temp in TEMPS:
    #                 print(f"TEMP={temp}")
    #                 model_key = f"multishot-{model_alias.get(model, model)}-pass-{PASS}"
    #                 if obj.get(model_key) \
    #                         and obj[model_key].get(f"temperature_{temp}"):
    #                     print("Already done")
    #                     continue
    #
    #                 func_str = obj['host_function_before_ef']['function_src']
    #                 func_str = func_str.replace('\\n', '\n')
    #                 url = obj['host_function_before_ef']['url']
    #                 offset_line_num = int(url.split("#L")[1].split('-')[0]) - 1
    #
    #                 fd = {
    #                     "url": url,
    #                     "func_str": add_line_nums(func_str, offset_line_num)
    #                 }
    #
    #                 metadata = llm_func(fd, model=model, temperature=temp)
    #
    #                 val = obj.get(model_key, {})
    #                 val[f"temperature_{temp}"] = metadata
    #                 obj[model_key] = val
    #                 newvalues = {"$set": {model_key: val}}
    #                 collection.update_one({'_id': obj['_id']}, newvalues)
