# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from typing import Optional
import os
import yaml
from git import Repo, exc


def get_env():
    try:
        repo = Repo(os.getcwd(), search_parent_directories=True)
    except exc.InvalidGitRepositoryError:
        print(f"Environment {os.getcwd()} is not a valid git repository.")
        return None

    if "SYSTEM_TEAMFOUNDATIONCOLLECTIONURI" in os.environ:
        return AzurePipelinesEnv(repo)
    else:
        return GitEnv(repo)


class Env(object):
    def __init__(self) -> None:
        root = self.repo_root
        self.CONFIG_FILE = "metrics.yml"
        self.DEFAULT_TARGET_BRANCH = "main"

        config_file_path = os.path.join(root, self.CONFIG_FILE)
        if os.path.exists(config_file_path):
            with open(config_file_path) as fp:
                self.cfg = yaml.safe_load(fp)
                if self.cfg is None:
                    self.cfg = {}
        else:
            print(
                f"{self.CONFIG_FILE} does not exist at the root {root} of the repo,"
                " metrics will not be recorded."
            )
            self.cfg = {}

    @property
    def config_file(self) -> str:
        return self.CONFIG_FILE

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
    def columns(self) -> int:
        return self.cfg.get("columns", 2)

    @property
    def span(self) -> int:
        return self.cfg.get("span", 30)

    @property
    def ewma_span(self) -> int:
        return self.cfg.get("ewma_span", 5)

    @property
    def monitoring_span(self) -> int:
        return self.cfg.get("monitoring_span", 50)

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

    @property
    def pr_user(self) -> str:
        return self.cfg.get("pr_user", "cimetrics")

    @property
    def monitoring_columns(self) -> int:
        return self.cfg.get("monitoring_columns", 2)

    @property
    def groups(self) -> dict:
        return self.cfg.get("groups", {"Metrics": ".*"})


class GitEnv(Env):
    _target_branch = None

    def __init__(self, repo) -> None:
        self.repo = repo
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

    @property
    def target_branch(self) -> str:
        if self._target_branch is not None:
            return self._target_branch

        self._target_branch = os.environ.get("CIMETRICS_TARGET_BRANCH")
        if self._target_branch is not None:
            return self._target_branch

        print(
            f"Target branch defaulting to {self.DEFAULT_TARGET_BRANCH}. Set CIMETRICS_TARGET_BRANCH env var to change it."
        )
        self._target_branch = self.DEFAULT_TARGET_BRANCH
        return self._target_branch

    def build_url_by_id(self, build_id) -> str:
        return f"{build_id}"

    @property
    def build_url(self) -> str:
        return self.build_url_by_id(self.build_id)

    @property
    def build_id(self) -> str:
        return "2"

    @property
    def build_number(self) -> str:
        return "0000.0"


class AzurePipelinesEnv(GitEnv):
    @property
    def build_id(self) -> str:
        return os.environ["BUILD_BUILDID"]

    @property
    def build_number(self) -> str:
        return os.environ["BUILD_BUILDNUMBER"]

    @property
    def is_pr(self) -> bool:
        return "SYSTEM_PULLREQUEST_SOURCEBRANCH" in os.environ

    @property
    def target_branch(self) -> str:
        return os.environ.get(
            "SYSTEM_PULLREQUEST_TARGETBRANCH", self.DEFAULT_TARGET_BRANCH
        )

    @property
    def branch(self) -> Optional[str]:
        short = None
        if self.is_pr:
            short = os.environ["SYSTEM_PULLREQUEST_SOURCEBRANCH"]
        else:
            ref = os.environ["BUILD_SOURCEBRANCH"]
            for prefix in ["refs/heads/", "refs/tags/", "refs/pull/"]:
                if ref.startswith(prefix):
                    short = ref[len(prefix) :]
                    break
            assert short, f"Unsupported ref type: {ref}"
        return short

    @property
    def pull_request_id(self) -> str:
        if self.is_pr:
            return os.environ["SYSTEM_PULLREQUEST_PULLREQUESTNUMBER"]
        else:
            return self.cfg["monitoring_issue"]

    @property
    def repo_id(self) -> str:
        return os.environ["BUILD_REPOSITORY_ID"]

    @property
    def repo_name(self) -> str:
        return os.environ["BUILD_REPOSITORY_NAME"]

    def build_url_by_id(self, build_id) -> str:
        prefix = os.environ["SYSTEM_TEAMFOUNDATIONSERVERURI"]
        project = os.environ["SYSTEM_TEAMPROJECT"]
        return f"{prefix}{project}/_build/results?buildId={build_id}&view=results"

    @property
    def build_url(self) -> str:
        return self.build_url_by_id(self.build_id)
