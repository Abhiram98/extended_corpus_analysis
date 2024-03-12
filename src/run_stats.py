import os

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from collections import defaultdict
import numpy as np
import matplotlib.patheffects as pe
import copy
import pickle

from evaluator.ef_evaluator_cli_impl import EFEvaluatorCli
from perform_sampling import get_all_responses, get_samples

import sys


# print(sys.argv[1:])

def convert_to_ints(df):
    cols = ['hf_loc',
            'candidates_count',
            'best_candidate_simscore',
            'best_candidate_offby',
            'bc_offby_s',
            'bc_offby_e',
            'top1_simscore',
            'top3_simscore',
            'top5_simscore',
            'top1_offby',
            'top3_offby',
            'top5_offby',
            '1pc_tol',
            '2pc_tol',
            '3pc_tol']

    for c in cols:
        df[c] = df[c].astype(int)


def extract_raw_results(df, top_n, tolerance):
    convert_to_ints(df)
    # oracle_instaces = len([i for i in df['doc_id'].isna() if not i])
    # jetgpt_suggestions = len([i for i in df['candidates_count'] if i >0])
    best_exact_match = len([i for i in df['best_candidate_offby'] if i == 0])

    column_map_top_n = {
        1: 'top1_offby',
        3: 'top3_offby',
        5: 'top5_offby'
    }

    column_map_tolerance = {
        1: '1pc_tol',
        2: '2pc_tol',
        3: '3pc_tol'
    }

    results = pd.Series(
        df[column_map_top_n.get(top_n)] <= df[column_map_tolerance.get(tolerance)])

    df_results = pd.DataFrame(zip(df['doc_id'], results), columns=['doc_id', 'result'])
    return df_results


def draw_plots(all_dfs, param, title, measure='f1'):
    TEMPS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0,
             1.2]
    ITERS = list(range(10))
    heatmap_data = []
    for temp in TEMPS:
        hd = []
        for itval in ITERS:
            hd.append(all_dfs[temp][itval].loc[param][measure])
        heatmap_data.append(hd)

    # data = heatmat_data['top5_3']
    # data.append(copy.copy(data[-1]))
    data = heatmap_data[::-1]
    ax = sns.heatmap(data, xticklabels=np.arange(1, 11), yticklabels=TEMPS[::-1],
                     cmap='binary', cbar=False)
    ax.set_xlabel("Iterations", size=20)
    ax.set_ylabel("Temperature", size=20)
    # cbar = ax.collections[0].colorbar
    # cbar.ax.tick_params(labelsize=20)

    for i, x, in enumerate(ax.get_xticks()):
        for j, y in enumerate(ax.get_yticks()):
            plt.annotate(
                '{:.1%}'.format(data[j][i]), (x - .4, y + .125),
                color='white',
                size=22,
                path_effects=[pe.withStroke(linewidth=2, foreground="black")]
            )
    ax.tick_params(axis='both', which='major', labelsize=20)
    plt.title(title)
    plt.show()


def get_settings_hash(settings):
    # IF_BODY
    # PREV_ASSIGNMENT
    # KEEP_ADJUSTED_CANDIDATE_ONLY
    # MAX_METHOD_LOC_THRESHOLD
    # MIN_METHOD_LOC_THRESHOLD

    # settings = {
    #     "IF_BODY": True,
    #     "PREV_ASSIGNMENT": True,
    #     "KEEP_ADJUSTED_CANDIDATE_ONLY": True,
    #     "MAX_METHOD_LOC_THRESHOLD": 0.88
    # }
    key = []
    key += ['IF_BODY'] if settings.get('IF_BODY') else []
    key += ['PREV_ASSIGNMENT'] if settings.get('PREV_ASSIGNMENT') else []
    key += ['KEEP_ADJUSTED_CANDIDATE_ONLY'] if settings.get('KEEP_ADJUSTED_CANDIDATE_ONLY') else []
    key += [f'MAX_METHOD_LOC_THRESHOLD_{settings["MAX_METHOD_LOC_THRESHOLD"]}'.replace(".", "_")] \
        if settings.get('MAX_METHOD_LOC_THRESHOLD', 1) < 1 else []
    key += [f'MIN_METHOD_LOC_THRESHOLD{settings["MIN_METHOD_LOC_THRESHOLD"]}'.replace(".", "_")] \
        if settings.get('MIN_METHOD_LOC_THRESHOLD', 0) > 0 else []
    # print(key)
    if key == []:
        return 'no-setting'
    return "-".join(key)


if __name__ == '__main__':
    temperature = 1.2
    samples = list(range(10))
    # passes = [0,1,2]
    heatmat_data = defaultdict(list)
    all_dfs = defaultdict(dict)
    # settings = {
    #     'IF_BODY': False,
    #     'PREV_ASSIGNMENT': False,
    #     'KEEP_ADJUSTED_CANDIDATE_ONLY': False,
    #     'MAX_METHOD_LOC_THRESHOLD': 1.0,
    #     'MIN_METHOD_LOC_THRESHOLD': 0.0
    # }
    settings = {
        'IF_BODY': True,
        'PREV_ASSIGNMENT': True,
        'KEEP_ADJUSTED_CANDIDATE_ONLY': True,
        'MAX_METHOD_LOC_THRESHOLD': 0.88,
        'MIN_METHOD_LOC_THRESHOLD': 0.0
    }

    # '64dc0ba2708d3e16a01d0fc2'

    ranking = 'popheat'
    model = 'gpt-3'
    # db_str = 'extract_function/ef1_stats_copy'
    db_str = 'extract_function/ef1_stats_resampling'
    dataset = db_str.split('/')[1]
    top_n = 5
    tolerance = 3
    itval = 9

    settings_hash = get_settings_hash(settings)

    # llm_responses = get_all_responses(db_str, model=model, temperature=temperature, iteration=itval+1)
    print(f"{settings_hash=}")
    try:
        os.mkdir(f'../data/pickle/stats/{dataset}')
    except:
        pass

    if ("recalls_3pc.pickle" in os.listdir('.')):
        with open("recalls_3pc.pickle", 'rb') as f:
            recalls = pickle.load(f)
    else:
        recalls = []

    if (f"{settings_hash}-{ranking}-{model}-p{min(samples)}-{max(samples)}.pickle"
            in os.listdir(f'../data/pickle/stats/{dataset}')):
        with open(f"../data/pickle/{dataset}/{settings_hash}-{ranking}-{model}.pickle", 'rb') as f:
            hits_and_misses = pickle.load(f)
    else:
        hits_and_misses = defaultdict(list)
        # recalls = []

        print(f"setting temp={temperature}")
        hd = defaultdict(list)
        for s_no in samples:
            print(f"setting iter={itval}")
            args = ['jetgpt_eval', '-db', db_str,
                    '-fld-name', f'jetgpt_ranking_sample_{s_no}', '-rank', ranking, '-temp', str(temperature),
                    '-shot-type', 'ms', '-heuristics', 'TT',
                    '-settings_key', get_settings_hash(settings),
                    # '-csv',
                    '-iterations', str(itval)]
            df = EFEvaluatorCli().run(args)

            df_results = extract_raw_results(df, top_n, tolerance)
            results = df_results.to_dict(orient='records')
            print(f"recall = {sum(df_results['result']) / len(df_results)}")
            print(len(df))
            recalls.append(sum(df_results['result']) / len(df_results))
            for r in results:
                doc_id = r['doc_id']
                hit = r['result']
                hits_and_misses[doc_id].append(hit)

        # with open(
        #         f"../data/pickle/stats/{dataset}/{settings_hash}-{ranking}-{model}-p{min(passes)}-{max(passes)}.pickle",
        #         'wb') \
        #         as f:
        #     # pickle.dump(all_dfs, f)
        #     print("skipped pickling")
        print(len(recalls), len(set(recalls)), np.mean(recalls), np.std(recalls))

        # with open("recalls_3pc.pickle", 'wb') as f:
        #     pickle.dump(recalls, f)

        # 64.6


