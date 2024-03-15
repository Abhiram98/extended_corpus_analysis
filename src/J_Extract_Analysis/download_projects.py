import json
import os
from typing import List, Dict

from git import Repo

PROJECTS_REPO = "/Users/malindamacstudio/Documents/Reseach_Extract_Method/PROJECTS/"


def read_project_file(file_path: str) -> List[Dict[str, str]]:
    with open(file_path, 'r') as file:
        json_data = json.load(file)

    details_list = []

    for repo_info in json_data.values():
        github_info = repo_info.get('github', {})
        owner = github_info.get('owner', '')
        repository = github_info.get('repository', '')
        github_link = github_info.get('github_link', '')
        stars = github_info.get('stars', 0)
        details_list.append({'owner': owner, 'repository': repository, 'github_link': github_link, 'stars': stars})
        print(owner+"/"+repository+","+stars)

    return details_list


def analyse_download_projects(file_path):
    projects = read_project_file(file_path)
    for project in projects:
        repo_clone(project['github_link'] + ".git", PROJECTS_REPO, project['owner'] + '/' + project['repository'])


def repo_clone(url, location, repo_name):
    if os.path.exists(location + repo_name):
        return
    os.makedirs(location + repo_name)
    print("Repo is downloading to :" + location + "/" + repo_name)
    Repo.clone_from(url=url, to_path=location + "/" + repo_name)


if __name__ == '__main__':
    analyse_download_projects('resource/projects.json')
