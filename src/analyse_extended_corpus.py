import json
import subprocess
import click
import pandas as pd
# from pymongo import MongoClient
from collections import Counter, defaultdict
import numpy as np
import matplotlib.pyplot as plt

from parse_jextract import convert2csv, within_tolerance


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
        # hf_loc = len(obj['host_function_before_ef']['function_src'].split('\\n'))
        func_src = obj['host_function_before_ef']['function_src'].replace('\\n', '\n')
        hf_loc = func_src[func_src.find('{'):func_src.rfind('}') + 1].count('\n') + 1 - 2
        try:
            liveref_data = obj['liveref_analysis']['rank_by_size']
        except Exception as e:
            print("no liveref data")
            liveref_data = None

        try:
            em_assist_data = obj['jetgpt_ranking']['llm_multishot_data']['temperature_1.0'] \
                ['rank_by_popularity_times_heat']
        except Exception as e:
            print("No EM Assist data")
            raise

        project_data[project_name].append({
            "projectName": project_name,
            "sha": obj['sha_before_ef'],
            "filename": obj['host_function_before_ef']['filename'],
            "functionName": obj['function_name'],
            "lineStart": obj['oracle']['line_start'],
            "lineEnd": obj['oracle']['line_end'],
            "hfLoc": hf_loc,
            "liveref_analysis": liveref_data,
            "em_assist": em_assist_data
        })
        all_proj.append(project_name)

        all_shas.append(obj['sha_before_ef'])
        ef_locs.append(obj['oracle']['line_end'] - obj['oracle']['line_start'] + 1)

    print(Counter(all_proj))
    sha_counter = Counter(all_shas).values()
    print(len(sha_counter))
    print(np.mean(list(sha_counter)))
    print(f"{min(ef_locs)=}")
    print(f"{max(ef_locs)=}")

    for pname in project_data.keys():
        with open(f"{pname}-data.json", 'w') as f:
            json.dump(project_data[pname], f, indent=1)


class JExtractAnalyser():
    def __init__(self, projects_root_dir, project_name,
                 data_file, jextract_out_dir,
                 tolerance_pct=3, topn=5, tolerance_loc=False):

        self.jextract_out_dir = jextract_out_dir
        self.data_file = data_file
        self.tolerance_loc = tolerance_loc
        self.topn = topn
        self.tolerance_pct = tolerance_pct
        self.project_name = project_name
        self.projects_root_dir = projects_root_dir

        with open(self.data_file) as f:
            self.data = json.load(f)

        self.update_completed()

    def change_git(self, commit_hash):
        subprocess.run([
            "git", "-C", f"{self.projects_root_dir}/{self.project_name}",
            "restore", "."
        ])

        subprocess.run([
            "git", "-C", f"{self.projects_root_dir}/{self.project_name}",
            "checkout", "-f", commit_hash
        ])

    def analyse(self):
        hits_and_misses = []
        # tolerance_pct = 3

        no_sug = 0
        # LIMIT = 1010
        all_base_dirs = []
        unreadable = 0
        hf_lens = []
        ef_lens = []
        hits = []

        for i, ref in enumerate(self.data):
            if i not in self.completed:
                hits_and_misses.append(False)
                continue
            # if i > LIMIT:
            #     break
            # if i not in completed:
            #     continue

            function_name = ref['functionName']
            oracle_start, oracle_end, hf_loc, sha = ref['lineStart'], ref['lineEnd'], ref['hfLoc'], ref['sha']
            relpath = f"{self.projects_root_dir}/{self.project_name}/{ref['filename']}"
            base_dir = relpath.split('src')[0] + 'src'
            all_base_dirs.append(base_dir)
            # if base_dir!=f'projects/{project_name}/src':
            #     continue

            self.change_git(ref['sha'])

            try:
                convert2csv(["--jextract-out", f"{self.jextract_out_dir}/{self.project_name}-{i}",
                             "--base-dir", base_dir],
                            standalone_mode=False)
            except:
                print("Coudn't read data.")
                hits_and_misses.append(False)
                with open(f"{self.jextract_out_dir}/{self.project_name}-{i}.csv", "w") as f:
                    f.write("JExtract internal error.")
                unreadable += 1
                continue

            df = pd.read_csv(f"{self.jextract_out_dir}/{self.project_name}-{i}.csv")


            if df.columns[0] == 'JExtract internal error.':
                hits_and_misses.append(False)
                continue

            # s2 = df[
            #     df['function_name'] == function_name
            #     ]
            # suggestions = df[
            #     (df['function_name'] == function_name) &
            #     (df['source_filename'] == relpath)
            #     ]
            suggestions = df

            if len(suggestions) > 0:
                found = False
                for _, per_func_suggestions in suggestions.groupby("function_signature"):
                    found = found or self.hit_miss_from_suggestions(hf_loc,
                                                           oracle_end, oracle_start, per_func_suggestions)
                if found:
                    hits_and_misses.append(True)
                    hf_lens.append(hf_loc)
                    ef_lens.append(oracle_end - oracle_start + 1)
                    hits.append(i)
                else:
                    hits_and_misses.append(False)
            else:
                hits_and_misses.append(False)
                print("no suggestions found.")
                no_sug += 1

        # convert_jextract(["--jextract-out", "JExtractOut/CoreNLP-1",
        #                  "--base-dir", "projects/CoreNLP/src"],
        #                  standalone_mode=False)

        print(f"Recall={sum(hits_and_misses) / len(hits_and_misses)}")
        print(f"{len(hits_and_misses)=}")
        print(f"{sum(hits_and_misses)=}")
        # print(f"{no_sug=}")
        # print(Counter(all_base_dirs))
        # print(f"{unreadable=}")
        # print(f"{np.mean(hf_lens)=}")
        # print(f"{np.mean(ef_lens)=}")

        outfile = f"{self.jextract_out_dir}/hits_and_misses-{self.project_name}-JExtract.json"
        with open(outfile, "w") as f:
            json.dump(hits_and_misses, f, indent=1)
        print(f"Hits and misses written to outfile={outfile}")
        return hits

    def hit_miss_from_suggestions(self, hf_loc, oracle_end,
                                  oracle_start, suggestions):
        for sug in suggestions['loc_suggestion'].to_list()[:self.topn]:
            sug_start, sug_end = sug[1:-1].split(',')
            sug_start = int(sug_start)
            sug_end = int(sug_end)
            if within_tolerance(
                    oracle_start, oracle_end,
                    sug_start, sug_end,
                    self.tolerance_pct, hf_loc,
                    tolerance_loc=self.tolerance_loc
            ):
                return True
        return False

    def update_completed(self):
        completed = []
        # LIMIT = 1010
        for i, ref in enumerate(self.data):

            # if (ref['lineEnd'] - ref['lineStart'] + 1) >= 0.88 * ref['hfLoc']:
            #     print("too large EM")
            #     continue
            # if ref['hfLoc'] <= 3:
            #     continue

            # if i > LIMIT:
            #     break
            try:
                with open(f"{self.jextract_out_dir}/{self.project_name}-{i}") as f:
                    file_contents = f.read()
                    first_line = file_contents.split("\n")[0]
            except FileNotFoundError:
                continue
            try:
                if first_line.startswith("foundFile"):
                    parts = file_contents.split('\n')
                    foundFile = parts[0].split('=')[1] == 'true'
                    foundMethod = parts[1].split('=')[1] == 'true'
                    noSrc = parts[2].split('=')[1] == 'false'
                    if foundFile and foundMethod and noSrc:
                        completed.append(i)
                else:
                    dotfile, func_signature, em_suggestion = first_line.split("	")
                    completed.append(i)
            except:
                pass

        print("completed.", len(completed))
        self.completed = completed
        with open(f"{self.jextract_out_dir}/{self.project_name}-completed.json", 'w') as f:
            json.dump(completed, f, indent=1)


def analyse_intellij():
    with open("intellij-community-data.json") as f:
        data = json.load(f)
    pass


def analyse_other(project_name, key, tolerance=3, topn=5, tolerance_loc=False):
    with open(f"{project_name}-data.json") as f:
        data = json.load(f)
    with open(f"{project_name}-completed.json") as f:
        completed = json.load(f)

    hits_and_misses = []
    hf_lens = []
    ef_lens = []
    hits = []

    for i, d in enumerate(data):
        if i not in completed:
            hits_and_misses.append(False)
            continue
        # obj = all_objs[i]

        ref = data[i]
        oracle_start, oracle_end, hf_loc = ref['lineStart'], ref['lineEnd'], ref['hfLoc']
        liveref_data = ref[key]

        if not liveref_data:
            hits_and_misses.append(False)
            continue

        found = False
        for ld in liveref_data[:topn]:
            other_start, other_end = ld['line_start'], ld['line_end']
            if within_tolerance(oracle_start, oracle_end,
                                other_start, other_end, tolerance=tolerance,
                                hf_loc=hf_loc, tolerance_loc=tolerance_loc):
                hits_and_misses.append(True)
                found = True
                hf_lens.append(hf_loc)
                ef_lens.append(oracle_end - oracle_start + 1)
                hits.append(i)
                break

        if not found:
            hits_and_misses.append(False)

    print(f"{len(completed)=}")
    print(f"{sum(hits_and_misses)=}")
    print(f"{sum(hits_and_misses) / len(hits_and_misses)=}")
    print(f"{np.mean(hf_lens)=}")
    print(f"{np.mean(ef_lens)=}")

    with open(f"hits_and_misses-{project_name}-{key}.json", "w") as f:
        json.dump(hits_and_misses, f, indent=1)

    return hits


def analyse_missed(h1, h2, project_name):
    with open(f"{project_name}-data.json") as f:
        data = json.load(f)

    missed = [j for i, j in enumerate(data) if i in set(h1).intersection(set(h2))]
    hflocs = [i['hfLoc'] for i in missed]
    efLocs = [i['lineEnd'] - i['lineStart'] + 1 for i in missed]

    print(f"{np.mean(hflocs)=}")
    print(f"{np.mean(efLocs)=}")
    print(f"{min(hflocs)=}")
    print(f"{min(efLocs)=}")

    print(f"{max(hflocs)=}")
    print(f"{max(efLocs)=}")
    plt.hist(hflocs)
    plt.show()


def analyse_hits(project_name,
                 topn,
                 tolerance,
                 tolerance_loc,
                 completed_only=False):
    with open(f"hits_and_misses-{project_name}-em_assist.json") as f:
        em_hits = json.load(f)
    with open(f"hits_and_misses-{project_name}-liveref_analysis.json") as f:
        lref_hits = json.load(f)
    with open(f"hits_and_misses-{project_name}-JExtract.json") as f:
        j_hits = json.load(f)

    with open(f"{project_name}-completed.json") as f:
        completed = json.load(f)

    with open(f"{project_name}-data.json") as f:
        data = json.load(f)

    assert len(em_hits) == len(lref_hits) == len(j_hits) == len(data)

    hf_em, hf_lr, hf_j, actual, hf_completed = [], [], [], [], []

    for i, d in enumerate(data):
        hfloc = d['hfLoc']

        if completed_only and i not in completed:
            actual.append(hfloc)
            continue

        actual.append(hfloc)
        hf_completed.append(hfloc)

        if i < len(em_hits) and em_hits[i]:
            hf_em.append(hfloc)
        if i < len(lref_hits) and lref_hits[i]:
            hf_lr.append(hfloc)
        if i < len(j_hits) and j_hits[i]:
            hf_j.append(hfloc)

    print(f"{np.mean(hf_em)=}")
    print(f"{np.mean(hf_lr)=}")
    print(f"{np.mean(hf_j)=}")

    hf_em = [i if i < 100 else 100 for i in hf_em]
    hf_lr = [i if i < 100 else 100 for i in hf_lr]
    hf_j = [i if i < 100 else 100 for i in hf_j]
    hf_completed = [i if i < 100 else 100 for i in hf_completed]

    bins = np.arange(0, 100, 5)
    if completed_only:
        plt.hist([hf_em, hf_lr, hf_j, hf_completed], bins=bins,
                 label=['EM-Assist', 'Liveref', 'JExtract', 'completed'])
    else:
        plt.hist([hf_em, hf_lr, hf_j, actual], bins=bins,
                 label=['EM-Assist', 'Liveref', 'JExtract', 'actual'])
    plt.xlabel("Host method length")
    plt.ylabel("Frequency")
    plt.xticks(bins)
    plt.legend(loc='upper right')
    tolerance_str = '-loc' if tolerance_loc else '%'
    plt.title(f"{project_name}\n{topn=}, {tolerance=}{tolerance_str}")
    plt.show()


@click.command(help='This command analyses the output of jextract to compute recall.')
@click.option("--projects_root_dir", help="parent directory containing all projects. "
    , default='../projects')
@click.option("--project_name")
@click.option("--data_file", help="Path to data file containing extract method oracle.")
@click.option("--jextract_out_dir", help="Output directory of jextract.")
@click.option("--tolerance_pct", help="tolerance %", type=int, default=3)
@click.option("--top_n_candidates", help='number of top candidates to select', default=5, type=int)
def analyse_data( projects_root_dir,project_name,
                 data_file, jextract_out_dir,
                 tolerance_pct, top_n_candidates):
    JExtractAnalyser(projects_root_dir,project_name,
                     data_file, jextract_out_dir,
                     tolerance_pct, top_n_candidates).analyse()


if __name__ == '__main__':
    analyse_data()
    # main()
    # topn = 5
    # tolerance = 5
    # tolerance_loc = False
    # tolerance = 2
    # tolerance_loc = True

    # update_completed("intellij-community")
    # update_completed("CoreNLP")
    # #
    # analyse_other("CoreNLP", 'liveref_analysis', tolerance=tolerance, topn=topn, tolerance_loc=tolerance_loc)
    # analyse_other("intellij-community", 'liveref_analysis', tolerance=tolerance, topn=topn, tolerance_loc=tolerance_loc)
    # analyse_other("CoreNLP", 'em_assist', tolerance=tolerance, topn=topn, tolerance_loc=tolerance_loc)
    # h1 = analyse_other("intellij-community", 'em_assist', tolerance=tolerance, topn=topn, tolerance_loc=tolerance_loc)
    # analyse("CoreNLP", tolerance_pct=tolerance, topn=topn, tolerance_loc=tolerance_loc)
    # h2 = analyse("intellij-community", tolerance_pct=tolerance, topn=topn, tolerance_loc=tolerance_loc)
    # #
    # analyse_hits("CoreNLP",
    #              topn=topn,
    #              tolerance=tolerance,
    #              tolerance_loc=tolerance_loc
    #              )
    # analyse_hits("intellij-community",
    #              topn=topn,
    #              tolerance=tolerance,
    #              tolerance_loc=tolerance_loc,
    #              completed_only=True)

    # analyse_missed(h2, h1, "intellij-community")

    # analyse_intellij()

# platform/analysis-api/src/com/intellij/codeInsight/intention/preview/IntentionPreviewInfo.java
