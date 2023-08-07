import ast
import base64
import json
import os
import re
import shutil
import xml.etree.ElementTree as ET

import requests
from pip._internal.vcs import git
import xml.dom.minidom as md


def get_env_variable(name):
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Environment variable '{name}' not set.")
    return value


def updateLog4jFileContent(log4j_path):
    with open(log4j_path, "r", encoding="UTF-8") as file:
        xml_data = file.read()

    dom = md.parseString(xml_data)

    properties_element = dom.getElementsByTagName("Properties")
    if len(properties_element) == 0:
        properties_element = dom.createElement("Properties")
        dom.documentElement.appendChild(properties_element)
    else:
        properties_element = properties_element[0]

    default_pattern_layout_element = None
    for property_element in properties_element.getElementsByTagName("Property"):
        if property_element.getAttribute("name") == "defaultPatternLayout":
            default_pattern_layout_element = property_element
            break

    if default_pattern_layout_element is not None:
        default_pattern_layout_element.firstChild.nodeValue = CUSTOM_MESSAGE
    else:
        new_property_element = dom.createElement("Property")
        new_property_element.setAttribute("name", "defaultPatternLayout")
        new_property_element.appendChild(dom.createTextNode(CUSTOM_MESSAGE))
        properties_element.appendChild(new_property_element)

    # Get the root element and find <PatternLayout> elements directly under it
    root_element = dom.documentElement
    pattern_layout_elements = root_element.getElementsByTagName(
        "PatternLayout")

    for pattern_layout_element in pattern_layout_elements:
        # Check if the <PatternLayout> element is directly under the root element
        if pattern_layout_element.parentNode == root_element:
            # Remove the existing <Property> element inside <PatternLayout>
            for child_element in pattern_layout_element.childNodes[:]:
                if child_element.nodeType == child_element.ELEMENT_NODE and child_element.tagName == "Property":
                    pattern_layout_element.removeChild(child_element)

            pattern_layout_element.setAttribute(
                "pattern", "${defaultPatternLayout}")

    # Get the XML content as a string with the UTF-8 encoding declaration
    xml_content = dom.toxml()

    # Remove any existing XML version declarations from the xml_content
    xml_content_without_version = re.sub(r'<\?xml[^>]*\?>', '', xml_content)

    # Add the encoding declaration to the xml_content string
    xml_content_with_encoding = f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_content_without_version}'

    # Write the string content to the file
    with open(log4j_path, "w", encoding="UTF-8") as file:
        file.write(xml_content_with_encoding)


def update_log4j_config(projectId, repo_path, repo_name):
    repo = git.Repo(repo_path)

    log4j_files = repo.git.ls_files("*log4j2*.xml").splitlines()

    for log4j_file in log4j_files:
        print(f"Updating {log4j_file} ....")
        log4j_path = os.path.join(repo_path, log4j_file)
        updateLog4jFileContent(log4j_path)

        # Commit changes
        repo.index.add([log4j_path])
        print(f"staging the changes in the file: {log4j_path}")

    repo.index.commit(GITLAB_COMMIT_MESSAGE)
    print(f"committed the changes")

    # Push changes
    new_branch = repo.create_head(GITLAB_SOURCE_BRANCH)
    new_branch.checkout()
    repo.remotes.origin.push(new_branch)
    print(f"pushing to {new_branch} branch")

    create_merge_request(projectId, repo_name)


def create_merge_request(projectId, repo_name):
    project_url = f"{GITLAB_URL}/api/v4/projects/{projectId}/merge_requests"
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
    code_owners = get_code_owners(projectId)
    payload = {
        "source_branch": GITLAB_SOURCE_BRANCH,
        "target_branch": GITLAB_TARGET_BRANCH,
        "title": GITLAB_COMMIT_MESSAGE,
        "description": f"Resolve SRE-741",
        "remove_source_branch": True,
        "squash": True,
        "auto_merge_strategy": "merge_when_pipeline_succeeds",
        "reviewers": code_owners
    }

    response = requests.post(project_url, headers=headers, json=payload)
    merge_request_url = response.json().get("web_url")

    if merge_request_url:
        print(f"Merge request created for {repo_name}")
        print(f"Merge request URL: {merge_request_url}")
    else:
        print(f"Failed to create merge request for {repo_name}")

    updateOutputJson({
        "source_repository": project_url,
        "mr_link": merge_request_url,
        "source_branch": GITLAB_SOURCE_BRANCH,
        "target_branch": GITLAB_TARGET_BRANCH,
        "status": merge_request_url if "created" else "not_created"
    })


def get_code_owners(projectId):
    codeowners_url = f"{GITLAB_URL}/api/v4/projects/{projectId}/repository/files/CODEOWNERS?ref={GITLAB_TARGET_BRANCH}"
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
    response = requests.get(codeowners_url, headers=headers)

    if response.status_code == 200:
        content = response.json().get("content")
        if content:
            # Decode the base64 content and extract code owners
            code_owners_content = base64.b64decode(content).decode("utf-8")
            code_owners = re.findall(r"@[\w-]+", code_owners_content)
            return code_owners

    return []  # Return an empty list if CODEOWNERS file not found or other errors


def updateOutputJson(newRepositoryMetadata):
    existing_merge_requests = []
    if os.path.exists(OUTPUT_JSON):
        existing_merge_requests = []
        with open(OUTPUT_JSON, "r") as json_file:
            data_from_file = json.load(json_file)
            existing_merge_requests = data_from_file

    existing_merge_requests.append(newRepositoryMetadata)

    with open(OUTPUT_JSON, "w") as json_file:
        json.dump(existing_merge_requests, json_file, indent=2)


def cloneRepoAndUpdateLog4j(projectId, repo_name, repo_path, repo_url):
    if not os.path.exists(repo_path):
        print(f"cloning the repo {repo_name}")
        git.Repo.clone_from(repo_url.format(token=GITLAB_TOKEN), repo_path)
    else:
        print(
            f"Repository already exists for {repo_name}. Removing repo.")
        shutil.rmtree(repo_path)
        cloneRepoAndUpdateLog4j(projectId, repo_name, repo_path, repo_url)

    update_log4j_config(projectId, repo_path, repo_name)


def main():
    for projectId, repo_url in MICROSERVICE_REPOS.items():
        repo_name = repo_url.split("/")[-1].split(".")[0]
        repo_path = os.path.join(REPO_CLONE_DIR, repo_name)
        cloneRepoAndUpdateLog4j(projectId, repo_name, repo_path, repo_url)


GITLAB_URL = get_env_variable("GITLAB_URL")
GITLAB_TOKEN = get_env_variable("GITLAB_TOKEN")
GITLAB_SOURCE_BRANCH = get_env_variable("GITLAB_SOURCE_BRANCH")
GITLAB_TARGET_BRANCH = get_env_variable("GITLAB_TARGET_BRANCH")
CUSTOM_MESSAGE = get_env_variable("CUSTOM_MESSAGE")
GITLAB_COMMIT_MESSAGE = get_env_variable("GITLAB_COMMIT_MESSAGE")
REPO_CLONE_DIR = get_env_variable("REPO_CLONE_DIR")
OUTPUT_JSON = get_env_variable("OUTPUT_JSON")
MICROSERVICE_REPOS_JSON = get_env_variable("MICROSERVICE_REPOS")
MICROSERVICE_REPOS = ast.literal_eval(MICROSERVICE_REPOS_JSON)

if __name__ == "__main__":
    main()
