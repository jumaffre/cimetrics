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
IMAGE_BRANCH_NAME = "metrics-devops"
IMAGE_PATH = "_cimetrics/diff.png"


class GithubPRPublisher(object):
    def __init__(self):
        self.env = get_env()
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
            f"{self.github_url}/git/refs/heads/master",
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
            f"{self.github_url}/contents/IMAGE_BRANCH_NAME/image{datetime.datetime.now()}.png",
            data=json.dumps(params),
            headers=self.request_header,
        )
        json_rep = json.loads(rep.text)
        if "content" in json_rep:
            return json_rep["content"]["download_url"]
        else:
            raise Exception("Failed to upload image")

    def publish_comment(self, image_report_url):
        params = {}
        params[
            "body"
        ] = f"Performance report: \n ![images]({image_report_url}) \n **Have a look before merging** :bar_chart: :eyes: :thumbsup:"

        print(f"Publishing comment to pull request {self.pull_request_id}")
        rep = requests.post(
            f"{self.github_url}/issues/{self.pull_request_id}/comments",
            data=json.dumps(params),
            headers=self.request_header,
        )


if __name__ == "__main__":

    publisher = GithubPRPublisher()

    publisher.create_image_branch()

    encoded_image = None
    with open(IMAGE_PATH, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read())

    image_url = publisher.upload_image(str(encoded_image.decode()))
    publisher.publish_comment(image_url)
