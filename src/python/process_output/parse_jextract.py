import json
import click
import os
import pandas as pd
# from pymongo import MongoClient


def get_function_name(func_signature: str):
    # private void addToHistory(java.lang.String)
    name = func_signature.split("(")[0].split(" ")[-1]
    return name


def get_filename(dot_name, base_dir):
    # junit.swingui.TestRunner
    filename = base_dir + '/' + dot_name.replace('.', '/') + '.java'
    return filename


def convert2loc(em_suggestion: str, code_str: str):
    start, end = em_suggestion[1:].split(':')
    start = int(start)
    end = int(end)

    start_line = code_str[:start].count('\n') + 1
    end_line = code_str[:start + end].count('\n') + 1

    return start_line, end_line

@click.group()
def cli():
    pass


@cli.command()
@click.option("--jextract-out", help='path to jextract output file', default=None)
@click.option("--base-dir", help='root directory of the source code.', default=None)
@click.option("--dest-dir", default=None, help='Where to store the resulting csv file')
def convert2csv(jextract_out: str, base_dir: str, dest_dir: str):
    if dest_dir is None:
        dest_dir = os.path.dirname(jextract_out)

    if jextract_out is None or base_dir is None:
        raise Exception("Param should have value.")

    with open(jextract_out) as f:
        jextract_data = f.read().split(';\n')

    if "." in  os.path.basename(jextract_out):
        basename, ext = os.path.basename(jextract_out).split(".")
    else:
        basename = os.path.basename(jextract_out)
    data = []

    for jd in jextract_data:
        if jd == '':
            continue
        dotfile, func_signature, em_suggestion = jd.split("	")
        filename = get_filename(dotfile, base_dir)
        file_not_found = False
        while not os.path.isfile(filename):
            dotfile = ".".join(dotfile.split('.')[:-1])
            if dotfile=='':
                file_not_found = True
                break
            filename = get_filename(dotfile, base_dir)

        if file_not_found:
            continue

        with open(filename, 'rb') as f:
            code_str = f.read().decode(errors='replace')

        func_name = get_function_name(func_signature)
        loc_suggestion = convert2loc(em_suggestion, code_str)

        data.append(
            (filename, func_name, func_signature, loc_suggestion)
        )

    pd.DataFrame(data, columns=['source_filename', 'function_name', 'function_signature', 'loc_suggestion']). \
        to_csv(f"{dest_dir}/{basename}.csv", index=False)

    return data


def within_tolerance(oracle_start, oracle_end,
                     other_start, other_end,
                     tolerance, hf_loc,
                     tolerance_loc=False):
    offby = abs(int(oracle_start) - int(other_start)) + \
            abs(int(oracle_end) - int(other_end))
    if tolerance_loc:
        tolerance_lines = tolerance
    else:
        tolerance_lines = int(hf_loc * (tolerance / 100))
    if 0 < offby <= tolerance_lines:
        print("within tolerance.")
        if tolerance_lines==1:
            print("Found within 1loc.")
    return offby <= tolerance_lines


@cli.command()
@click.option("--jextract_parsed_csv", help="csv file with the parse jextract output")
@click.option("--tolerance-pct", type=int, help="csv file with the parse jextract output")
@click.option("--tolerance-loc", type=bool,
              default=False, help="Whether to count tolerance "
                                  "in terms of loc of pct")
@click.option("--project", default=None, help="Project to evaluate.")
@click.option("--topn", default=3, type=int, help="Use topn recommendations.")
def get_hitmiss(jextract_parsed_csv,
                tolerance_pct, tolerance_loc, project, topn):
    df = pd.read_csv(jextract_parsed_csv)
    df = df.groupby(['source_filename', 'function_name']).head(topn)

    client = MongoClient('localhost', 27017)
    db_name = 'extract_function'
    collection_name = 'ef1_stats'
    collection = client[db_name][collection_name]

    # query = collection.find({
    #     "$and": [
    #         {
    #             "llm_multishot_data": {
    #                 "$exists": True
    #             }
    #         },
    #     ]
    # })
    query = collection.find({})
    all_objs = list(query)

    hits_and_misses = []
    for obj in all_objs:
        project_name, class_name, function_name, \
            local_filename, local_path = obj['project_name'], obj['class_name'], \
            obj['function_name'], obj['local_filename'], \
            obj['local_path']
        function_src = obj['host_function_before_ef']['function_src']

        if project is not None and project_name != project:
            continue

        relpath = "ef_xu_oracle" + local_filename.split("ef_xu_oracle")[1]
        suggestions = df[
            (df['function_name'] == function_name) &
            (df['source_filename'] == relpath)
            ]

        oracle_start, oracle_end = obj['oracle']['line_start'], obj['oracle']['line_end']

        jextract_result = {"hit": False,
                           "raw": suggestions.to_dict(orient='records')}
        # if len(suggestions) > 0:
        if False:
            for sug in suggestions['loc_suggestion'].to_list():
                sug_start, sug_end = sug[1:-1].split(',')
                sug_start = int(sug_start)
                sug_end = int(sug_end)
                if within_tolerance(
                        oracle_start, oracle_end,
                        sug_start, sug_end,
                        tolerance_pct, len(function_src),
                        tolerance_loc=tolerance_loc
                ):
                    jextract_result = {"hit": True,
                                       "raw": suggestions.to_dict(orient='records')}
                    break
        else:
            # print("checking if any suggestions from file match line numbers")
            #
            # print("jextract had no suggestions")
            suggestions_file = df[df['source_filename'] == relpath]
            for sug in suggestions_file['loc_suggestion'].to_list():
                sug_start, sug_end = sug[1:-1].split(',')
                sug_start = int(sug_start)
                sug_end = int(sug_end)
                if within_tolerance(
                        oracle_start, oracle_end,
                        sug_start, sug_end,
                        tolerance_pct, len(function_src),
                        tolerance_loc=tolerance_loc):
                    jextract_result = {"hit": True,
                                       "raw": suggestions_file.to_dict(orient='records')}
                    break

        if not jextract_result['hit']:
            print("Not found.")
            print("loc: ", oracle_end - oracle_start)

        obj['jextract_result'] = jextract_result
        hits_and_misses.append(jextract_result['hit'])

    print(hits_and_misses)
    print("Recall raw:", sum(hits_and_misses))
    print("Oracle count:", len(hits_and_misses))
    print("Recall: ", sum(hits_and_misses) / len(hits_and_misses))
    return hits_and_misses


def combine_csvs(*csv_files):
    df = pd.read_csv(csv_files[0])
    for c in csv_files[1:]:
        df1 = pd.read_csv(c)
        df = pd.concat([df, df1])

    return df


if __name__ == '__main__':
    # convert_jextract(["--jextract-out", "../TBE/jextract/out/JextractOut-JHotDraw.txt",
    #                  "--base-dir", "ef_xu_oracle/projects/JHotDraw5.2/sources"],
    #                  standalone_mode=False)
    # convert_jextract(["--jextract-out", "../TBE/jextract/out/JextractOut-junit.txt",
    #                   "--base-dir", "ef_xu_oracle/projects/junit3.8/src"],
    #                  standalone_mode=False)
    # convert_jextract(["--jextract-out", "../TBE/jextract/out/JextractOut-MyWebMarket.txt",
    #                   "--base-dir", "ef_xu_oracle/projects/MyWebMarket/src"],
    #                  standalone_mode=False)
    # convert_jextract(["--jextract-out", "../TBE/jextract/out/JextractOut-wikidev-filters.txt",
    #                   "--base-dir", "ef_xu_oracle/projects/wikidev-filters/src"],
    #                  standalone_mode=False)
    # convert_jextract(["--jextract-out", "../TBE/jextract/out/JextractOut-junit-top3.txt",
    #                   "--base-dir", "ef_xu_oracle/projects/junit3.8/src"],
    #                  standalone_mode=False)

    # convert_jextract(["--jextract-out", "../TBE/jextract/out/JextractOut-junit.txt",
    #                   "--base-dir",
    #                   # "/Users/abhiram/Downloads/junit3.8 2/src"
    #                   "ef_xu_oracle/projects/junit3.8/src"
    #                   ],
    #                  standalone_mode=False)

    # df = combine_csvs("../TBE/jextract/out/JextractOut-JHotDraw.csv",
    #                   "../TBE/jextract/out/JextractOut-junit.csv",
    #                   "../TBE/jextract/out/JextractOut-MyWebMarket.csv",
    #                   "../TBE/jextract/out/JextractOut-wikidev-filters.csv")
    # df.to_csv("../TBE/jextract/out/JextractOut-combined.csv", index=False)

    # get_hitmiss(["--jextract_parsed_csv",
    #              '../TBE/jextract/out/JextractOut-combined.csv',
    #              # '../TBE/jextract/out/JextractOut-junit.csv',
    #              "--tolerance-pct", "1",
    #              # "--tolerance-loc", "True",
    #              # "--project", "MyWebMarket",
    #              # "--project", "junit3.8",
    #              # "--project", "JHotDraw5.2",
    #              "--topn", "3"],
    #             standalone_mode=False)

    cli()