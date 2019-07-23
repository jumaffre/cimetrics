import requests
import json
import sys
import base64
import datetime
import os

#
# This script should only run on the CI against Pull Request builds
#

# To get from the CI environment variables
USERNAME = "jumaffre"
REPO = "jumaffre/metrics-devops"

# Always the same for metrics-devops
IMAGE_BRANCH_NAME = "metrics-devops"

def get_github_token():
    return os.environ['GITHUB_TOKEN']

def get_pull_request_id():
    return os.environ['SYSTEM_PULLREQUEST_PULLREQUESTNUMBER']

# REST specific
REQUEST_HEADERS = {'content-type': 'application/json', 'Authorization': f"token {get_github_token()}"}
GITHUB_URL = f"https://api.github.com/repos/{REPO}"
BRANCH_CREATION_URL = f"{GITHUB_URL}/git/refs"
IMAGE_UPLOADING_URL = f"{GITHUB_URL}/contents/{IMAGE_BRANCH_NAME}/image{datetime.datetime.now()}.png"

# Create branch to push images to 
def create_branch():
    # Does not do anything if the branch already exists
    params = {}
    params["ref"] = f"refs/heads/{IMAGE_BRANCH_NAME}"

    # TODO: Should get the hash of master instead?
    params["sha"] = "ab6b38a54d04097a2924330c7730be8f339ab9a1"

    print(f"Creating branch {json.dumps(params)}")
    rep = requests.post(BRANCH_CREATION_URL, data=json.dumps(params), headers=REQUEST_HEADERS)
    print(rep.text)

def upload_image(encoded_image):
    params = {}
    params["message"] = "Uploading an image"
    params["branch"] = IMAGE_BRANCH_NAME
    params["content"] = encoded_image

    print(f"Uploading image to branch {IMAGE_BRANCH_NAME}")
    rep = requests.put(IMAGE_UPLOADING_URL, data=json.dumps(params), headers=REQUEST_HEADERS)
    json_rep = json.loads(rep.text)
    if "content" in json_rep:
        return json_rep["content"]["download_url"]
    else:
        raise Exception("Failed to upload image")

def publish_comment(pull_request_id, image_report_url):
    params = {}
    params["body"] = f"Performance report: \n ![images]({image_report_url}) \n **Have a look before merging** :bar_chart: :eyes: :thumbsup:"

    print(f"Publishing comment to pull request {pull_request_id}")
    rep = requests.post(f"{GITHUB_URL}/issues/{str(pull_request_id)}/comments", data=json.dumps(params), headers=REQUEST_HEADERS)

if __name__ == '__main__':
    # Try to create the branch to upload images to

    create_branch()

    encoded_image = None
    image_path = "_pymetrics/diff.png"
    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read())

    # Upload base64 image to dedicated branch
    image_url = upload_image(str(encoded_image.decode()))

    # Comment on the pull request
    pull_request_id = get_pull_request_id()
    publish_comment(pull_request_id, image_url)
