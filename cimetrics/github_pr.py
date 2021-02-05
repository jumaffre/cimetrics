# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import requests
import json
import sys
import base64
import datetime
import os

from cimetrics.env import get_env

# Always the same for metrics-devops
IMAGE_BRANCH_NAME = "cimetrics"
IMAGE_PATH = "_cimetrics/diff.png"
COMMENT_PATH = "_cimetrics/diff.txt"


class GithubPRPublisher(object):
    def __init__(self):
        self.env = get_env()
        if self.env is None:
            return

        self.request_header = {
            "content-type": "application/json",
            "Authorization": f"token {self.env.github_token}",
        }
        self.github_url = f"https://api.github.com/repos/{self.env.repo_id}"
        self.pull_request_id = self.env.pull_request_id

    def create_image_branch(self):
        # Does not do anything if the branch already exists
        params = {}
        params["ref"] = f"refs/heads/{IMAGE_BRANCH_NAME}"
        rep = requests.get(
            f"{self.github_url}/git/refs/heads/main",
            data="",
            headers=self.request_header,
        )
        json_rep = json.loads(rep.text)
        params["sha"] = json_rep["object"]["sha"]

        print(f"Creating branch {json.dumps(params)}")
        rep = requests.post(
            f"{self.github_url}/git/refs",
            data=json.dumps(params),
            headers=self.request_header,
        )

    def upload_image(self, encoded_image):
        params = {}
        params["message"] = "Uploading an image"
        params["branch"] = IMAGE_BRANCH_NAME
        params["content"] = encoded_image

        print(f"Uploading image to branch {IMAGE_BRANCH_NAME}")
        rep = requests.put(
            f"{self.github_url}/contents/{IMAGE_BRANCH_NAME}/image{datetime.datetime.now()}.png",
            data=json.dumps(params),
            headers=self.request_header,
        )
        json_rep = json.loads(rep.text)
        if "content" in json_rep:
            return json_rep["content"]["download_url"]
        else:
            raise Exception("Failed to upload image")

    def first_self_comment(self):
        rep = requests.get(
            f"{self.github_url}/issues/{self.pull_request_id}/comments",
            headers=self.request_header,
        )

        for comment in rep.json():
            login = comment.get("user", {}).get("login")
            if login == self.env.pr_user:
                return comment["id"]
        return None

    def publish_comment(self, image_report_url, comment):
        params = {}
        params["body"] = f"{comment}\n![images]({image_report_url})"

        comment_id = self.first_self_comment()
        if comment_id is None:
            print(f"Publishing comment to pull request {self.pull_request_id}")
            rep = requests.post(
                f"{self.github_url}/issues/{self.pull_request_id}/comments",
                data=json.dumps(params),
                headers=self.request_header,
            )
        else:
            print(
                f"Updating comment {comment_id} on pull request {self.pull_request_id}"
            )
            rep = requests.patch(
                f"{self.github_url}/issues/comments/{comment_id}",
                data=json.dumps(params),
                headers=self.request_header,
            )


if __name__ == "__main__":

    env = get_env()
    if env is None:
        print("Skipping publishing of PR comment (env)")
        sys.exit(0)

    publisher = GithubPRPublisher()

    publisher.create_image_branch()

    encoded_image = None
    with open(os.path.join(env.repo_root, IMAGE_PATH), "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read())
    comment = ""
    with open(os.path.join(env.repo_root, COMMENT_PATH), "r") as comment_file:
        comment = comment_file.read()

    image_url = publisher.upload_image(str(encoded_image.decode()))
    publisher.publish_comment(image_url, comment)
