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


def extract_precision_recall(df):
    convert_to_ints(df)
    oracle_instaces = len([i for i in df['doc_id'].isna() if not i])
    jetgpt_suggestions = len([i for i in df['candidates_count'] if i >0])
    best_exact_match = len([i for i in df['best_candidate_offby'] if i==0])



    top1_1 = len(df[df.top1_offby <= df['1pc_tol']])
    top1_2 = len(df[df.top1_offby <= df['2pc_tol']])
    top1_3 = len(df[df.top1_offby <= df['3pc_tol']])
    p1_1 = top1_1/jetgpt_suggestions
    r1_1 = top1_1/oracle_instaces
    p1_2 = top1_2/jetgpt_suggestions
    r1_2 = top1_2/oracle_instaces
    p1_3 = top1_3/jetgpt_suggestions
    r1_3 = top1_3/oracle_instaces
    f1_1 = 2*(p1_1 * r1_1)/ (p1_1 + r1_1)
    f1_2 = 2 * (p1_2 * r1_2) / (p1_2 + r1_2)
    f1_3 = 2 * (p1_3 * r1_3) / (p1_3 + r1_3)

    top3_1 = len(df[df.top3_offby <= df['1pc_tol']])
    top3_2 = len(df[df.top3_offby <= df['2pc_tol']])
    top3_3 = len(df[df.top3_offby <= df['3pc_tol']])
    p3_1 = top3_1/jetgpt_suggestions
    r3_1 = top3_1/oracle_instaces
    p3_2 = top3_2/jetgpt_suggestions
    r3_2 = top3_2/oracle_instaces
    p3_3 = top3_3/jetgpt_suggestions
    r3_3 = top3_3/oracle_instaces
    f3_1 = 2*(p3_1 * r3_1)/ (p3_1 + r3_1)
    f3_2 = 2 * (p3_2 * r3_2) / (p3_2 + r3_2)
    f3_3 = 2 * (p3_3 * r3_3) / (p3_3 + r3_3)

    top5_1 = len(df[df.top5_offby <= df['1pc_tol']])
    top5_2 = len(df[df.top5_offby <= df['2pc_tol']])
    top5_3 = len(df[df.top5_offby <= df['3pc_tol']])
    p5_1 = top5_1/jetgpt_suggestions
    r5_1 = top5_1/oracle_instaces
    p5_2 = top5_2/jetgpt_suggestions
    r5_2 = top5_2/oracle_instaces
    p5_3 = top5_3/jetgpt_suggestions
    r5_3 = top5_3/oracle_instaces
    f5_1 = 2*(p5_1 * r5_1)/ (p5_1 + r5_1)
    f5_2 = 2 * (p5_2 * r5_2) / (p5_2 + r5_2)
    f5_3 = 2 * (p5_3 * r5_3) / (p5_3 + r5_3)

    topb_1 = len(df[df.best_candidate_offby <= df['1pc_tol']])
    topb_2 = len(df[df.best_candidate_offby <= df['2pc_tol']])
    topb_3 = len(df[df.best_candidate_offby <= df['3pc_tol']])
    pb_1 = topb_1/jetgpt_suggestions
    rb_1 = topb_1/oracle_instaces
    pb_2 = topb_2/jetgpt_suggestions
    rb_2 = topb_2/oracle_instaces
    pb_3 = topb_3/jetgpt_suggestions
    rb_3 = topb_3/oracle_instaces
    fb_1 = 2*(pb_1 * rb_1)/ (pb_1 + rb_1)
    fb_2 = 2 * (pb_2 * rb_2) / (pb_2 + rb_2)
    fb_3 = 2 * (pb_3 * rb_3) / (pb_3 + rb_3)

    columns = ['sample', 'precision', 'recall', 'f1']
    data = [
        ('top1_1', p1_1, r1_1, f1_1), ('top1_2', p1_2, r1_2, f1_2), ('top1_3', p1_3, r1_3, f1_3),
        ('top3_1', p3_1, r3_1, f3_1), ('top3_2', p3_2, r3_2, f3_2), ('top3_3', p3_3, r3_3, f3_3),
        ('top5_1', p5_1, r5_1, f5_1), ('top5_2', p5_2, r5_2, f5_2), ('top5_3', p5_3, r5_3, f5_3),
        ('topb_1', pb_1, rb_1, fb_1), ('topb_2', pb_2, rb_2, fb_2), ('topb_3', pb_3, rb_3, fb_3)
    ]
    df_summary = pd.DataFrame(data, columns=columns)
    df_summary = df_summary.set_index('sample')
    return df_summary


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
    ax = sns.heatmap(data, xticklabels=np.arange(1,11), yticklabels=TEMPS[::-1],
                     cmap='binary', cbar=False)
    ax.set_xlabel("Iterations", size=20)
    ax.set_ylabel("Temperature", size=20)
    # cbar = ax.collections[0].colorbar
    # cbar.ax.tick_params(labelsize=20)

    for i, x, in enumerate(ax.get_xticks()):
        for j, y in enumerate(ax.get_yticks()):
            plt.annotate(
                '{:.1%}'.format(data[j][i]), (x-.4, y+.125),
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
    if key== []:
        return 'no-setting'
    return "-".join(key)


if __name__=='__main__':
    TEMPS = [
        0.0, 0.2, 0.4, 0.6, 0.8,
             1.0,
             1.2
    ]
    ITERS = list(range(10))
    # ITERS = [6, 7]
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
    ranking = 'popheat'
    model = 'gpt-3'
    db_str = 'extract_function/ef1_copy'
    dataset = db_str.split('/')[1]

    settings_hash = get_settings_hash(settings)
    print(f"{settings_hash=}")
    try:
        os.mkdir(f'../data/pickle/{dataset}')
    except:
        pass

    if (f"{settings_hash}-{ranking}-{model}.pickle" in os.listdir(f'../data/pickle/{dataset}')):
        with open(f"../data/pickle/{dataset}/{settings_hash}-{ranking}-{model}.pickle", 'rb') as f:
            all_dfs = pickle.load(f)
    else:
        for temp in TEMPS:
            print(f"setting temp={temp}")
            hd = defaultdict(list)
            for itval in ITERS:
                    print(f"setting iter={itval}")
                    args =['jetgpt_eval', '-db', db_str,
                           '-fld-name', f'jetgpt_ranking_{model}', '-rank', ranking, '-temp', str(temp),
                           '-shot-type', 'ms', '-heuristics', 'TT',
                           '-settings_key', get_settings_hash(settings),
                           # '-csv',
                           '-iterations', str(itval)]
                    df = EFEvaluatorCli().run(args)
                    df_summary = extract_precision_recall(df)
                    hd['top5_1'].append(df_summary.loc['top5_1'].f1)
                    hd['top5_2'].append(df_summary.loc['top5_2'].f1)
                    hd['top5_3'].append(df_summary.loc['top5_3'].f1)
                    print(len(df))
                    all_dfs[temp][itval] = df_summary
            heatmat_data['top5_1'].append(hd['top5_1'])
            heatmat_data['top5_2'].append(hd['top5_2'])
            heatmat_data['top5_3'].append(hd['top5_3'])

        with open(f"../data/pickle/{dataset}/{settings_hash}-{ranking}-{model}.pickle", 'wb') as f:
            pickle.dump(all_dfs, f)

    param = 'top5_3'

    title = f"recall: {model}\nranking={ranking}, {param.split('_')[0]} candidates, {param.split('_')[1]}% tolerance"
    # title = ''
    draw_plots(all_dfs, param, title, measure='recall')