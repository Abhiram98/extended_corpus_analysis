from helpers import chatgpt_suggestions_evaluation
import matplotlib.pyplot as plt
import seaborn as sns
from itertools import zip_longest
import pandas as pd
from helpers import add_iter_data

def iter_vs_num_correct():
    df_gpt_3 = chatgpt_suggestions_evaluation('extract_function/ef1_copy', 'xu_dataset_evaluation_gpt_3.csv',
                                              model='gpt-3', write=False, do_processing=False)
    df_gpt_3_correct = df_gpt_3[df_gpt_3['result'] == 'OK']
    df_gpt_3_correct.groupby('temperature')

    add_iter_data(df_gpt_3_correct, 'extract_function/ef1_copy', 'gpt-3')

    max_iters = 10
    groups = df_gpt_3_correct.groupby('temperature')['iteration'].\
        apply(lambda x: [i for i in x if i >0]).\
        apply(lambda l: [len([j for j in l if j <= i]) for i in range(1, max_iters + 1)])

    fig, ax = plt.subplots()
    my_linestyles = [
        'solid',
        'dotted',
        'dashed',
        'dashdot',
        (0, (3, 1, 1, 1))
    ]
    for i, temp in enumerate(groups.index):
        ax.plot(groups[temp], label=temp, linestyle=my_linestyles[i % len(my_linestyles)])
    ax.legend()
    ax.set_xlabel("Iterations")
    ax.set_ylabel("Number of Extract-Function Suggestions")
    xticks = [i+1 for i in list(ax.get_xticks())]
    ax.set_xticks(ax.get_xticks(), xticks)
    # plt.title("Valid EF suggestions per temperature")
    plt.show()


def draw_plots():
    df_gpt_3 = chatgpt_suggestions_evaluation('extract_function/ef1_copy', 'xu_dataset_evaluation_gpt_3.csv',
                                              model='gpt-3', write=False, do_processing=True)
    df_gpt_3_correct = df_gpt_3[df_gpt_3['result'] == 'OK']
    df_gpt_3_correct.groupby('temperature')['doc_id'].apply(lambda x: len(x)/122)

    df_gpt_3_incorrect = df_gpt_3[df_gpt_3['result'] != 'OK']
    df_gpt_3_incorrect.groupby('temperature')['doc_id'].apply(lambda x: len(x)/122)

if __name__ == '__main__':
    # draw_plots()
    iter_vs_num_correct()