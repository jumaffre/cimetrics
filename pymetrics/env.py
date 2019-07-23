import os
import yaml
from git import Repo

def get_env():
    if 'SYSTEM_TEAMFOUNDATIONCOLLECTIONURI' in os.environ:
        return AzurePipelinesEnv()
    else:
        return GitEnv()

class Env(object):
    def __init__(self) -> None:
        root = self.repo_root
        with open(os.path.join(root, 'metrics.yml')) as fp:
            self.cfg = yaml.safe_load(fp)

    @property
    def repo_root(self) -> str:
        # implemented by subclass
        raise NotImplementedError

    @property
    def mongo_db(self) -> str:
        return self.cfg['db']

    @property
    def mongo_collection(self) -> str:
        return self.cfg['collection']

    @property
    def mongo_connection(self) -> str:
        return os.environ['METRICS_MONGO_CONNECTION']

    @property
    def build_id(self):
        return None

    @property
    def is_pr(self):
        return False

class GitEnv(Env):
    def __init__(self) -> None:
        self.repo = Repo(os.getcwd(), search_parent_directories=True)
        super().__init__()
    
    @property
    def repo_root(self) -> str:
        return self.repo.working_tree_dir

    @property
    def branch(self) -> str:
        return self.repo.active_branch.name

    @property
    def commit(self) -> str:
        return self.repo.commit().hexsha

class AzurePipelinesEnv(GitEnv):
    @property
    def build_id(self) -> str:
        return os.environ['BUILD_BUILDID']

    @property
    def is_pr(self) -> bool:
        return 'SYSTEM_PULLREQUEST_SOURCEBRANCH' in os.environ

    @property
    def target_branch(self) -> str:
        assert self.is_pr
        return os.environ['SYSTEM_PULLREQUEST_SOURCEBRANCH']
    
    @property
    def branch(self) -> str:
        # CI checks out detached commit, must rely on env var.
        ref = os.environ['BUILD_SOURCEBRANCH']
        prefix = 'refs/heads/'
        assert prefix in ref, 'Unsupported ref type: ' + ref
        short = ref.replace(prefix, '')
        return short
