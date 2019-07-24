# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from typing import Optional
import os
import yaml
from git import Repo


def get_env():
    if "SYSTEM_TEAMFOUNDATIONCOLLECTIONURI" in os.environ:
        return AzurePipelinesEnv()
    else:
        return GitEnv()


class Env(object):
    def __init__(self) -> None:
        root = self.repo_root
        with open(os.path.join(root, "metrics.yml")) as fp:
            self.cfg = yaml.safe_load(fp)

    @property
    def repo_root(self) -> str:
        # implemented by subclass
        raise NotImplementedError

    @property
    def mongo_db(self) -> str:
        return self.cfg["db"]

    @property
    def mongo_collection(self) -> str:
        return self.cfg["collection"]

    @property
    def mongo_connection(self) -> str:
        return os.environ["METRICS_MONGO_CONNECTION"]

    @property
    def build_id(self):
        return None

    @property
    def is_pr(self):
        return False

    @property
    def github_token(self) -> str:
        return os.environ["GITHUB_TOKEN"]


class GitEnv(Env):
    def __init__(self) -> None:
        self.repo = Repo(os.getcwd(), search_parent_directories=True)
        super().__init__()

    @property
    def repo_root(self) -> str:
        return self.repo.working_tree_dir

    @property
    def branch(self) -> Optional[str]:
        if not self.repo.head.is_detached:
            return self.repo.active_branch.name
        tag_or_none = next(
            (tag.name for tag in self.repo.tags if tag.commit == self.repo.head.commit),
            None,
        )
        return tag_or_none

    @property
    def commit(self) -> str:
        return self.repo.commit().hexsha


class AzurePipelinesEnv(GitEnv):
    @property
    def build_id(self) -> str:
        return os.environ["BUILD_BUILDID"]

    @property
    def is_pr(self) -> bool:
        return "SYSTEM_PULLREQUEST_SOURCEBRANCH" in os.environ

    @property
    def target_branch(self) -> str:
        assert self.is_pr
        return os.environ["SYSTEM_PULLREQUEST_TARGETBRANCH"]

    @property
    def branch(self) -> Optional[str]:
        if self.is_pr:
            short = os.environ["SYSTEM_PULLREQUEST_SOURCEBRANCH"]
        else:
            ref = os.environ["BUILD_SOURCEBRANCH"]
            short = None
            for prefix in ["refs/heads/", "refs/tags/"]:
                if ref.startswith(prefix):
                    short = ref[len(prefix) :]
                    break
            assert short, f"Unsupported ref type: {ref}"
        return short

    @property
    def pull_request_id(self) -> str:
        assert self.is_pr
        return os.environ["SYSTEM_PULLREQUEST_PULLREQUESTNUMBER"]

    @property
    def repo_id(self) -> str:
        return os.environ["BUILD_REPOSITORY_ID"]
