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
    for obj in all_objs:
        url = obj['host_function_before_ef']['url']
        # proj = "/".join(url.split('https://github.com/')[1].split('/')[:2])
        project_name = url.split('https://github.com/')[1].split('/')[1]
        hf_loc = len(obj['host_function_before_ef']['function_src'].split('\\n'))
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

    print(Counter(all_proj))
    sha_counter = Counter(all_shas).values()
    print(len(sha_counter))
    print(np.mean(list(sha_counter)))

    for pname in project_data.keys():
        with open(f"{pname}-data.json", 'w') as f:
            json.dump(project_data[pname], f)



def analyse():
    with open("CoreNLP-data.json") as f:
        data = json.load(f)

    hits_and_misses = []
    tolerance_pct = 3

    no_sug = 0
    LIMIT = 100
    all_base_dirs = []

    for i, ref in enumerate(data):
        if i > LIMIT:
            break

        function_name = ref['functionName']
        oracle_start, oracle_end, hf_loc = ref['lineStart'], ref['lineEnd'], ref['hfLoc']
        relpath = f"projects/CoreNLP/{ref['filename']}"
        base_dir = relpath.split('src')[0] + 'src'
        all_base_dirs.append(base_dir)
        # if base_dir!='projects/CoreNLP/src':
        #     continue
        # git
        # restore.
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
            # hits_and_misses.append(False)
            with open(f"JExtractOut/CoreNLP-{i}.csv", "w") as f:
                f.write("JExtract internal error.")
            # continue

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
    pass
if __name__ == '__main__':
    main()
    analyse()
