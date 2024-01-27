import json
import subprocess

import pandas as pd
from pymongo import MongoClient
from collections import Counter, defaultdict
import numpy as np

from parse_jextract import convert_jextract, within_tolerance

def main():
    client = MongoClient('localhost', 27017)
    db_name = 'extract_function'
    collection_name = 'extended_corpus'
    collection = client[db_name][collection_name]
    all_objs = collection.find({})
    project_data = {"CoreNLP": [], "intellij-community": []}
    all_proj = []
    all_shas = []
    all_filenames = []
    data = []
    ef_locs = []
    for obj in all_objs:
        url = obj['host_function_before_ef']['url']
        # proj = "/".join(url.split('https://github.com/')[1].split('/')[:2])
        project_name = url.split('https://github.com/')[1].split('/')[1]
        hf_loc = len(obj['host_function_before_ef']['function_src'].split('\\n'))
        # func_src = obj['host_function_before_ef']['function_src'].replace('\\n', '\n')
        # hf_loc = func_src[func_src.find('{'):func_src.rfind('}')+1].count('\n')+1
        project_data[project_name].append({
            "projectName": project_name,
            "sha": obj['sha_before_ef'],
            "filename": obj['host_function_before_ef']['filename'],
            "functionName": obj['function_name'],
            "lineStart": obj['oracle']['line_start'],
            "lineEnd": obj['oracle']['line_end'],
            "hfLoc": hf_loc
        })
        all_proj.append(project_name)

        all_shas.append(obj['sha_before_ef'])
        ef_locs.append(obj['oracle']['line_end']-obj['oracle']['line_start']+1)

    print(Counter(all_proj))
    sha_counter = Counter(all_shas).values()
    print(len(sha_counter))
    print(np.mean(list(sha_counter)))
    print(f"{min(ef_locs)=}")
    print(f"{max(ef_locs)=}")

    for pname in project_data.keys():
        with open(f"{pname}-data.json", 'w') as f:
            json.dump(project_data[pname], f, indent=1)



def analyse():
    with open("CoreNLP-data.json") as f:
        data = json.load(f)

    hits_and_misses = []
    tolerance_pct = 3

    no_sug = 0
    # LIMIT = 1010
    all_base_dirs = []
    unreadable = 0

    for i, ref in enumerate(data):
        # if i > LIMIT:
        #     break

        function_name = ref['functionName']
        oracle_start, oracle_end, hf_loc = ref['lineStart'], ref['lineEnd'], ref['hfLoc']
        relpath = f"projects/CoreNLP/{ref['filename']}"
        base_dir = relpath.split('src')[0] + 'src'
        all_base_dirs.append(base_dir)
        # if base_dir!='projects/CoreNLP/src':
        #     continue

        subprocess.run([
            "git", "-C", "projects/CoreNLP",
            "restore", "."
        ])

        subprocess.run([
            "git", "-C", "projects/CoreNLP",
            "checkout", "-f", ref['sha']
        ])

        # with open(relpath) as f:
        #     hf_loc = f.read()

        try:
            convert_jextract(["--jextract-out", f"JExtractOut/CoreNLP-{i}",
                              "--base-dir", base_dir],
                             standalone_mode=False)
        except:
            print("Coudn't read data.")
            hits_and_misses.append(False)
            with open(f"JExtractOut/CoreNLP-{i}.csv", "w") as f:
                f.write("JExtract internal error.")
            unreadable += 1
            continue

        df = pd.read_csv(f"JExtractOut/CoreNLP-{i}.csv")
        # suggestions = df[
        #     (df['function_name'] == function_name) &
        #     (df['source_filename'] == relpath)
        #     ]
        suggestions = df

        if len(suggestions) > 0:
            found = False
            for sug in suggestions['loc_suggestion'].to_list():
                sug_start, sug_end = sug[1:-1].split(',')
                sug_start = int(sug_start)
                sug_end = int(sug_end)
                if within_tolerance(
                        oracle_start, oracle_end,
                        sug_start, sug_end,
                        tolerance_pct, hf_loc
                ):
                    hits_and_misses.append(True)
                    found = True
                    break
            if not found:
                hits_and_misses.append(False)
        else:
            hits_and_misses.append(False)
            print("no suggestions found.")
            no_sug+=1


    # convert_jextract(["--jextract-out", "JExtractOut/CoreNLP-1",
    #                  "--base-dir", "projects/CoreNLP/src"],
    #                  standalone_mode=False)

    print(f"{len(hits_and_misses)}")
    print(f"{sum(hits_and_misses)/len(hits_and_misses)}")
    print(f"{no_sug=}")
    print(Counter(all_base_dirs))
    print(f"{unreadable=}")

    with open("hits_and_misses.json", "w") as f:
        json.dump(hits_and_misses, f, indent=1)


def update_completed(project_name):
    with open(f"{project_name}-data.json") as f:
        data = json.load(f)

    completed = []
    # LIMIT = 1010
    for i, ref in enumerate(data):
        # if i > LIMIT:
        #     break
        try:
            with open(f"JExtractOut/{project_name}-{i}") as f:
                first_line = f.read().split("\n")[0]
        except FileNotFoundError:
            continue
        try:
            dotfile, func_signature, em_suggestion = first_line.split("	")
            completed.append(i)
        except:
            pass



    print("completed.", len(completed))
    with open(f"{project_name}-completed.json", 'w') as f:
        json.dump(completed, f, indent=1)


def analyse_intellij():
    with open("intellij-community-data.json") as f:
        data = json.load(f)
    pass



if __name__ == '__main__':
    main()
    # analyse()
    # update_completed("intellij-community")

    update_completed("CoreNLP")

    # update_completed("CoreNLP")

    # analyse_intellij()

# platform/analysis-api/src/com/intellij/codeInsight/intention/preview/IntentionPreviewInfo.java