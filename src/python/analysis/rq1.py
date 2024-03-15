import os
import pickle
from helpers import chatgpt_suggestions_evaluation
import matplotlib.pyplot as plt
import matplotlib
from matplotlib import ticker
import seaborn as sns
from itertools import zip_longest
import pandas as pd
from collections import Counter
import numpy as np
import itertools

hall_lambda = lambda x: "Hallucination: one-liner/whole-body" \
    if x in ['Selection is one line', 'Selection represents entire body function'] \
    else "Erroneous Suggestion"

def draw_invalid_plots(plot=True):
    df_gpt_3 = chatgpt_suggestions_evaluation('extract_function/ef1_copy', 'xu_dataset_evaluation_gpt_3.csv',
                                              model='gpt-3', write=False)
    df_palm = chatgpt_suggestions_evaluation('extract_function/ef1_copy', 'xu_dataset_evaluation_palm.csv',
                                             model='palm', write=False)
    df_gpt_4 = chatgpt_suggestions_evaluation('extract_function/ef1_gpt_4', 'xu_dataset_evaluation_gpt_4.csv',
                                              model='gpt-4', write=False)

    df_gpt_3_incorrect = df_gpt_3[df_gpt_3['result'] != 'OK']
    df_gpt_4_incorrect = df_gpt_4[df_gpt_4['result'] != 'OK']
    df_palm_incorrect = df_palm[df_palm['result'] != 'OK']

    df_gpt_3_incorrect['reason_processed'] = df_gpt_3_incorrect['reason'].apply(hall_lambda)
    df_gpt_4_incorrect['reason_processed'] = df_gpt_4_incorrect['reason'].apply(hall_lambda)
    df_palm_incorrect['reason_processed'] = df_palm_incorrect['reason'].apply(hall_lambda)

    # d1 = list(df_gpt_3_incorrect.groupby(['doc_id']).apply(lambda x: len(x)))
    # d2 = list(df_gpt_4_incorrect.groupby(['doc_id']).apply(lambda x: len(x)))
    # d3 = list(df_palm_incorrect.groupby(['doc_id']).apply(lambda x: len(x)))

    df_reasons_gpt_3 = df_gpt_3_incorrect.groupby(['reason_processed'])['doc_id']. \
        apply(lambda x: x)
    df_reasons_gpt_4 = df_gpt_4_incorrect.groupby(['reason_processed'])['doc_id']. \
        apply(lambda x: x)
    df_reasons_palm = df_palm_incorrect.groupby(['reason_processed'])['doc_id']. \
        apply(lambda x: x)

    reasons_log_scale = [
        ("Hallucination: one-liner/whole-body", True),
        # ('Selection is one line', True), #significant
        # ('Selection represents entire body function', False), #significant
        # ('Unable to extract method. Selected block should represent a set of statements or an expression',
        #                 True), #most significant
        # ('Unable to extract method. There are multiple exit points.', True), #insignificant
        # ('invalid extract function candidate', True) #insignificant
        ("Erroneous Suggestion", True)
    ]
    all_dfs = []
    for r, log_scale in reasons_log_scale:
        try:
            d1 = list(Counter(df_reasons_gpt_3[r]).values())
        except KeyError:
            d1 = []
        try:
            d2 = list(Counter(df_reasons_gpt_4[r]).values())
        except KeyError:
            d2 = []
        try:
            d3 = list(Counter(df_reasons_palm[r]).values())
        except KeyError:
            d3 = []
        data = [(i, f'gpt-3.5') for i in d1] + \
               [(i, f'gpt-4') for i in d2] + \
               [(i, f'palm') for i in d3]
        df = pd.DataFrame(data, columns=['count', 'model'])
        all_dfs.append(df)

        if plot:
            ax = sns.violinplot(data=df, x='model', y='count', cut=0,
                                inner=None, linewidth=0, saturation=0.4)
            sns.boxplot(data=df, x='model', y='count', width=0.1,
                        boxprops={'zorder': 2}, ax=ax
                        )

            if log_scale:
                ax.set_yscale('log', base=2)
            plt.title(r)
            # plt.ylim(0,128)
            plt.xlabel("model")
            plt.ylabel("count per function")
            plt.show()
    return all_dfs



def draw_plots_by_param(log_scale=False, custom_ax=None):
    if("RQ1.pickle" in os.listdir('data/pickle')):
        with open('data/pickle/RQ1.pickle', 'rb') as f:
            all_dfs = pickle.load(f)
    else:
        df_gpt_3 = chatgpt_suggestions_evaluation('extract_function/ef1_copy', 'xu_dataset_evaluation_gpt_3.csv',
                                                  model='gpt-3', write=False)
        df_palm = chatgpt_suggestions_evaluation('extract_function/ef1_copy', 'xu_dataset_evaluation_palm.csv',
                                                 model='palm', write=False)
        df_gpt_4 = chatgpt_suggestions_evaluation('extract_function/ef1_gpt_4', 'xu_dataset_evaluation_gpt_4.csv',
                                                  model='gpt-4', write=False)

        df_gpt_3_correct = df_gpt_3[df_gpt_3['result'] == 'OK']
        df_gpt_4_correct = df_gpt_4[df_gpt_4['result'] == 'OK']
        df_palm_correct = df_palm[df_palm['result'] == 'OK']

        d1 = list(df_gpt_3_correct.groupby(['doc_id']).apply(lambda x: len(x)))
        d2 = list(df_gpt_4_correct.groupby(['doc_id']).apply(lambda x: len(x)))
        d3 = list(df_palm_correct.groupby(['doc_id']).apply(lambda x: len(x)))

        xu_dataset_size = len(df_gpt_3.groupby(['doc_id']).apply(lambda x: len(x)))
        # d2 += [0] * (xu_dataset_size - len(d2))
        data = [(i, 'gpt-3.5') for i in d1] + \
               [(i, 'gpt-4') for i in d2] + \
               [(i, 'palm') for i in d3]

        df1 = pd.DataFrame(data, columns=['count', 'model'])
        # df1['model'] = df1['model'] + '- Valid Suggestions'

        # draw total suggestions
        d1 = list(df_gpt_3.groupby(['doc_id']).apply(lambda x: len(x)))
        d2 = list(df_gpt_4.groupby(['doc_id']).apply(lambda x: len(x)))
        d3 = list(df_palm.groupby(['doc_id']).apply(lambda x: len(x)))

        xu_dataset_size = len(df_gpt_3.groupby(['doc_id']).apply(lambda x: len(x)))
        # d2 += [0] * (xu_dataset_size - len(d2))
        data = [(i, 'gpt-3.5') for i in d1] + \
               [(i, 'gpt-4') for i in d2] + \
               [(i, 'palm') for i in d3]

        df2 = pd.DataFrame(data, columns=['count', 'model'])
        # df2['model'] = df2['model'] + '- All Suggestions'

        incorrect_dfs = draw_invalid_plots(plot=False)



        all_dfs = [
            (df2, 'All Suggestions'),
            (incorrect_dfs[1], 'Invalid Suggestions'),
            (incorrect_dfs[0], 'Not Useful Suggestions'),
            (df1, 'Applicable Suggestions'),
        ]
        with open('data/pickle/RQ1.pickle', 'wb') as f:
            pickle.dump(all_dfs, f)
    fig, ax_list= plt.subplots(nrows=1, ncols=4, sharey=True, sharex=True)
    ax_list_iter = iter(ax_list)
    for df, title in all_dfs:
        ax = next(ax_list_iter)

        violionplot = sns.violinplot(data=df, x='model', y='count', cut=0, ax=ax,
                       inner=None, linewidth=1, saturation=0.4, color='gray',
                       scale='width')
        for collection in violionplot.collections:
            if isinstance(collection, matplotlib.collections.PolyCollection):
                collection.set_edgecolor(collection.get_facecolor())
                collection.set_facecolor('none')

        box_plot = sns.boxplot(data=df, x='model', y='count',
                    width=0.1,
                    # boxprops={'zorder': 2},
                    boxprops=dict(zorder=2
                    # ,edgecolor='black'
                    ),
                    ax=ax,
                    meanline=True,
                    showmeans=True,
                    meanprops={
                        'color': 'black', 'lw': 2},
                    medianprops={'color': 'black'},
                    color='gray',
                    saturation=1
                    )

        if log_scale:
            ax.set_yscale('log', base=2)

        labels = [item.get_text() for item in ax.get_xticklabels()]
        model_iter = itertools.cycle(['gpt-3.5', 'gpt-4', 'palm'])
        for i, label in enumerate(labels):
            labels[i] = next(model_iter)
        ax.set_xticklabels(labels)

        ax.set_title(title)
        ax.set_ylabel('')

        means = df.groupby('model')['count'].mean()
        medians = df.groupby('model')['count'].median()
        x_offset = 0.4
        print(f"{medians=}")

        model_order = [
            'gpt-3.5',
            'gpt-4',
            'palm'
        ]
        for xtick in box_plot.get_xticks():
            box_plot.text(xtick + x_offset, medians[model_order[xtick]],
                          "\u03BC=%.2f" % medians[model_order[xtick]],
                          horizontalalignment='center', size='x-small', color='black', weight='semibold')

            box_plot.text(xtick + x_offset, means[model_order[xtick]],
                          "M=%.2f" % means[model_order[xtick]],
                          horizontalalignment='center', size='x-small', color='black', weight='semibold')

        # ax.spines['top'].set_visible(False)
        # ax.spines['right'].set_visible(False)
        # ax.spines['left'].set_visible(False)
        # [t.set_visible(False) for t in ax.get_yticklines()]
        # plt.set_ylim(0, 128)

    num_yticks = len(ax_list[0].get_yticks())
    print(f"{num_yticks=}")
    [ax.set_yticks([2**i for i in range(num_yticks+1)]) for ax in ax_list]
    ax_list[0].get_yaxis().set_major_formatter(ticker.ScalarFormatter())
    # ax_list[0].get_yaxis().get_major_formatter().labelOnlyBase = False
    # ax_list[0].set_ylabel('Count')
    # ax_list[0].spines['left'].set_visible(True)
    # [t.set_visible(True) for t in ax_list[0].get_yticklines()]

    # fig.ylim(0, 128)
    plt.yticks([2**i for i in range(num_yticks+1)])
    # plt..get_major_formatter().labelOnlyBase = False

    plt.show()


def draw_plots_by_llm(model, log_scale=True, ax=None, show=True):
    if(ax is None):
        fig, ax = plt.subplots()
    if model=='gpt-3':
        df = chatgpt_suggestions_evaluation('extract_function/ef1_copy', 'xu_dataset_evaluation_gpt_3.csv',
                                                  model='gpt-3', write=False)
    elif model=='gpt-4':
        df = chatgpt_suggestions_evaluation('extract_function/ef1_copy', 'xu_dataset_evaluation_palm.csv',
                                                 model='palm', write=False)
    elif model == 'palm':
        df = chatgpt_suggestions_evaluation('extract_function/ef1_gpt_4', 'xu_dataset_evaluation_gpt_4.csv',
                                                  model='gpt-4', write=False)

    df['result_processed'] = df['result'].apply(lambda x: x if 'OK' else 'FAIL')

    # distribution of total refactoring suggestions
    total_dist = list(df.groupby(['doc_id']).apply(lambda x: len(x)))

    df_result_group = df.groupby('result_processed')['doc_id'].apply(lambda  x:x)
    correct_dist = list(Counter(df_result_group['OK']).values())

    df_incorrect = df[df['result'] != 'OK']
    df_incorrect['reason_processed'] = df_incorrect['reason'].apply(hall_lambda)
    df_reasons = df_incorrect.groupby(['reason_processed'])['doc_id']. \
        apply(lambda x: x)
    # "Hallucination: one-liner/whole-body"
    # "Erroneous Suggestion"
    hall_dist = list(Counter(df_reasons["Hallucination: one-liner/whole-body"]).values())
    err_dist = list(Counter(df_reasons["Erroneous Suggestion"]).values())

    columns = ['Suggestions',
               'Count']
    data = [('Total Suggestions', i) for i in total_dist] +\
        [('Valid Suggestions', i) for i in correct_dist] +\
        [("Erroneous Suggestion", i) for i in err_dist] +\
        [("Hallucination: one-liner/whole-body", i) for i in hall_dist]
    df = pd.DataFrame(data, columns=columns)

    sns.violinplot(data=df, x='Suggestions', y='Count', cut=0, ax=ax,
                        inner=None, linewidth=0, saturation=0.4, color='gray')
    box_plot = sns.boxplot(data=df, x='Suggestions', y='Count', width=0.1,
                boxprops={'zorder': 2}, ax=ax, color='gray',
                meanline=True,
                showmeans=True,
                meanprops={
                    'color': 'black', 'lw': 2},
                )

    medians = df.groupby(['Suggestions'])['Count'].median()
    means = df.groupby(['Suggestions'])['Count'].mean()
    print(f"{means =}")
    print(f"{medians =}")
    vertical_offset = 1
    x_offset = 0.4
    suggestions_order = [
        'Total Suggestions',
        'Valid Suggestions',
        "Erroneous Suggestion",
        "Hallucination: one-liner/whole-body"
    ]
    for xtick in box_plot.get_xticks():
        box_plot.text(xtick + x_offset, medians[suggestions_order[xtick]], "\u03BC=%.2f" % medians[suggestions_order[xtick]],
                      horizontalalignment='center', size='x-small', color='black', weight='semibold')

        box_plot.text(xtick + x_offset, means[suggestions_order[xtick]] , "M=%.2f" % means[suggestions_order[xtick]],
                      horizontalalignment='center', size='x-small', color='black', weight='semibold')

    if log_scale:
        ax.set_yscale('log', base=2)
    ax.set_title(model.capitalize())
    plt.ylim(0, 128)
    ax.set_xticklabels(['All', 'Valid', 'Err', 'Hall'])

    if show:
        plt.show()


def draw_all_by_llm():
    fig, all_ax = plt.subplots(nrows=1, ncols=3, sharey=True)
    draw_plots_by_llm('gpt-3', log_scale=True, ax=all_ax[0], show=False)
    draw_plots_by_llm('gpt-4', log_scale=True, ax=all_ax[1], show=False)
    draw_plots_by_llm('palm', log_scale=True, ax=all_ax[2], show=False)
    num_ticks = len(all_ax[0].get_yticks())
    all_ax[0].set_yticks([int(2**i) for i in range(num_ticks+1)])
    plt.show()

if __name__ == '__main__':
    draw_plots_by_param(log_scale=True)
    # draw_invalid_plots()
    # draw_all_by_llm()