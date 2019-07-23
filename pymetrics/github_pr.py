import requests
import json
import sys

TOKEN = "0b0cbbcd28e5c4902c00b58614eac1bb952f71e3"
USERNAME = "jumaffre"

REQUEST_HEADERS = {'content-type': 'application/json', 'Authorization': 'token {}'.format(TOKEN)}
GITHUB_URL = "https://api.github.com/repos/jumaffre/metrics-devops/git/refs"

IMAGE_BRANCH_NAME = "images22"
REQUEST_CREATE_BRANCH = {"ref": "refs/heads/images22333", "sha": "ab6b38a54d04097a2924330c7730be8f339ab9a1"}


# Create branch to push images to 
def create_branch():
    # Does not do anything if the branch already exists
    print(f"Creating branch {REQUEST_CREATE_BRANCH}, head={REQUEST_HEADERS}")

    params = {}
    params["ref"] = "refs/heads/images22333"
    params["sha"] = "ab6b38a54d04097a2924330c7730be8f339ab9a1"

    rep = requests.post(GITHUB_URL, data=json.dumps(params), headers=REQUEST_HEADERS)
    print(rep.text)


if __name__ == '__main__':
    print("Hello there")
    create_branch()

    # For now, load image

    # TODO: 
    #   0. Get image
    #   1. Turn image into Base64 encoded version
    #   2. Upload image
    #   3. Public comment

