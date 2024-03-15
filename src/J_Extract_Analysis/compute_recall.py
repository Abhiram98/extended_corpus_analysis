import json
import os
import re
from collections import Counter
from typing import Dict

from git import Repo

J_EXTRACT_OUTPUT = "/Users/malindamacstudio/Documents/Reseach_Extract_Method/Files/OUTPUT/"
PROJECTS_ROOT_DIR = "/Users/malindamacstudio/Documents/Reseach_Extract_Method/PROJECTS/"
PROJECT_NAME = "apache_datasketches-java"
JEXTRACT_OUT_DIR = "/Users/malindamacstudio/Documents/Reseach_Extract_Method/Files/OUTPUT/"
TOLERANCE_PCT = 3
TOP_N_CANDIDATES = 5
ORACLE = "/Users/malindamacstudio/Documents/Reseach_Extract_Method/Files/Refacorings/Indexed/"


class OffsetNotFound(Exception):
    def __init__(self, message):
        self.message = message


def get_file_content_before_commit(repo_path, commit_hex, relative_file_path):
    repo = Repo(repo_path)

    # Resolve commit ID
    commit = repo.commit(commit_hex)
    if commit is None:
        raise ValueError(
            "The commit ID could not be resolved. Ensure the commit exists and the repository path is correct.")

    # Check for parent commit
    if not commit.parents:
        raise ValueError("This commit has no parent (it might be the initial commit).")

    parent_commit = commit.parents[0]

    # Find the blob for the file in the parent commit
    file_blob = parent_commit.tree / relative_file_path
    if file_blob is None:
        raise ValueError("File not found in the parent commit.")

    # Get file content as bytes and decode to string
    file_content = file_blob.data_stream.read().decode('utf-8')

    return file_content


def read_files_ending_with_integer(root_dir):
    """
    Iterates over a folder and its subfolders to read all files
    whose names end with an integer.
    """
    # A list to hold the content of files that match the criteria
    files_content = {}

    # Walking through the directory and its subdirectories
    for subdir, dirs, files in os.walk(root_dir):
        for file in files:
            # Checking if the file name (without extension) ends with an integer
            if file.rsplit('.', 1)[0].rstrip('0123456789').endswith('-') and file.rsplit('.', 1)[0][-1].isdigit():
                file_path = os.path.join(subdir, file)
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        files_content[int((file.split("-")[-1]))] = content
                except Exception as e:
                    print(f"Error reading file {file_path}: {e}")

    return files_content


def get_valid_outputs(j_extract_outputs: Dict[int, str]):
    valid_ids = []
    for id, file_contents in j_extract_outputs.items():
        first_line = file_contents.split("\n")[0]
        try:
            if first_line.startswith("foundFile"):
                parts = file_contents.split('\n')
                found_file = parts[0].split('=')[1] == 'true'
                found_method = parts[1].split('=')[1] == 'true'
                no_src = parts[2].split('=')[1] == 'false'
                if found_file and found_method and no_src:
                    valid_ids.append(id)
            else:
                dotfile, func_signature, em_suggestion = first_line.split("	")
                valid_ids.append(id)
        except:
            pass
    print("total outputs.", len(j_extract_outputs))
    print("total valid outputs.", len(valid_ids))
    return valid_ids


def read_oracle():
    json_files_content = {}
    for subdir, dirs, files in os.walk(ORACLE):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(subdir, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                        for refac in content:
                            json_files_content[refac["ID"]] = refac
                except Exception as e:
                    print(f"Error reading JSON file {file_path}: {e}")

    return json_files_content


def compute_recalls(j_extract_output, valid_j_extract_output, oracle):
    id_and_match = dict()
    off_set_not_founds = 0
    off_set_founds = 0
    non_parsed_suggestions = []
    for id in valid_j_extract_output:
        file_content = j_extract_output[id]
        oracle_em = oracle[id]
        oracle_start, oracle_end, hf_loc, sha = oracle_em["extracted_code_range_from_source_operation"]["start_line"], \
            oracle_em["extracted_code_range_from_source_operation"]["end_line"], oracle_em["length_host"], oracle_em[
            "sha"]
        file_path = oracle_em["extracted_code_range_from_source_operation"]["file_path"]
        project_name = oracle_em["projectName"]
        hm_file_content = get_file_content_before_commit(os.path.join(PROJECTS_ROOT_DIR, project_name, ""), sha,
                                                         relative_file_path=file_path)
        id_and_match[id] = "UNMATCHED"

        if j_extract_no_suggestions(file_content):
            id_and_match[id] = "NO_SUGGESTION"
        else:
            for suggestion in file_content.split("\n"):
                if len(suggestion) > 0:
                    try:
                        off_set_founds += 1
                        offsets = get_start_end_offset_from_j_extract_output(suggestion)
                        em_suggestion = get_j_extract_start_end_line_numbers(hm_file_content, offsets["start_offset"],
                                                                             offsets["end_offset"])
                        if suggestion_within_tolerance(oracle_start, oracle_end, em_suggestion["em_start_line"],
                                                       em_suggestion["em_end_line"], TOLERANCE_PCT, hf_loc):
                            id_and_match[id] = "MATCHED"
                            break
                    except OffsetNotFound as e:
                        off_set_not_founds += 1
                        non_parsed_suggestions.append(file_content)
                        print(e)
                        continue
    frequency_counter = Counter(non_parsed_suggestions)

    print(valid_j_extract_output, "valid outputs")
    print(frequency_counter)
    print(off_set_founds, " found")
    print(off_set_not_founds, " not found")
    print(sum(1 for k in id_and_match.values() if k), " matched cases")
    print(len(valid_j_extract_output), " total cases")
    print(sum(1 for k in id_and_match.values() if k) / 100 * len(valid_j_extract_output), " recall")


def j_extract_no_suggestions(file_content):
    """
    Check if J-Extract generates no suggestions for a given file's content, even when no other errors occur.
    """
    expected_content = """foundFile=true
foundMethod=true
noSource=false"""

    return file_content == expected_content
def suggestion_within_tolerance(oracle_start, oracle_end,
                                other_start, other_end,
                                tolerance, hf_loc,
                                tolerance_loc=False):
    offby = abs(int(oracle_start) - int(other_start)) + abs(int(oracle_end) - int(other_end))
    if tolerance_loc:
        tolerance_lines = tolerance
    else:
        tolerance_lines = int(hf_loc * (tolerance / 100))
    if 0 < offby <= tolerance_lines:
        print("within tolerance.")
        if tolerance_lines == 1:
            print("Found within 1loc.")
    return offby <= tolerance_lines


def get_start_end_offset_from_j_extract_output(em_suggestion: str):
    pattern = r".*?\te(\d+):(\d+);"
    match = re.match(pattern, em_suggestion)
    if match:
        # Process the numbers as needed
        number1, number2 = match.groups()
        return {"start_offset": int(number1), "end_offset": int(number1) + int(number2)}
    raise OffsetNotFound("offset values are not available in the suggestion")


def get_j_extract_start_end_line_numbers(hm_file_content: str, start_offset: int, end_offset: int):
    start_line = hm_file_content[:start_offset].count('\n') + 1
    end_line = hm_file_content[:end_offset].count('\n') + 1
    return {"em_start_line": start_line, "em_end_line": end_line}


def main():
    j_extract_output = read_files_ending_with_integer(JEXTRACT_OUT_DIR)
    valid_j_extract_output = get_valid_outputs(j_extract_output)
    oracle = read_oracle()
    compute_recalls(j_extract_output, valid_j_extract_output, oracle)
    print()


if __name__ == '__main__':
    main()
