# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import requests
import json
import sys
import base64
import datetime
import os
from azure.storage.blob import BlobServiceClient, ContentSettings

from cimetrics.env import get_env

# Always the same for metrics-devops
IMAGE_PATH = "_cimetrics/diff.png"
COMMENT_PATH = "_cimetrics/diff.txt"

AZURE_BLOB_URL = os.getenv("AZURE_BLOB_URL")
AZURE_WEB_URL = os.getenv("AZURE_WEB_URL")


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

    def upload_image_as_blob(self, contents):
        service = BlobServiceClient(account_url=AZURE_BLOB_URL)
        name = f"plot-{self.env.repo_name.replace('/', '-')}-{self.env.pull_request_id}.png"
        blob = service.get_blob_client(container="$web", blob=name)
        blob.upload_blob(
            contents,
            overwrite=True,
            content_settings=ContentSettings(
                content_type="image/png", cache_control="no-cache"
            ),
        )
        return f"{AZURE_WEB_URL}/{name}"

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

    encoded_image = None
    raw_image = None
    with open(os.path.join(env.repo_root, IMAGE_PATH), "rb") as image_file:
        raw_image = image_file.read()
        encoded_image = base64.b64encode(raw_image)
    comment = ""
    with open(os.path.join(env.repo_root, COMMENT_PATH), "r") as comment_file:
        comment = comment_file.read()

    assert (
        AZURE_BLOB_URL and AZURE_WEB_URL
    ), "Either AZURE_BLOB_URL or AZURE_WEB_URL is not set"
    image_url = publisher.upload_image_as_blob(raw_image)
    publisher.publish_comment(image_url, comment)
