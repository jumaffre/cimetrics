import os
import sys
import datetime
import yaml
import pymongo

def get_mongo_connection_string():
    return os.environ['METRICS_MONGO_CONNECTION']

# For now, only Azure Pipeline's environment variables are supported.

def get_settings():
    root = os.getenv('BUILD_SOURCEDIRECTORY')
    if not root:
        raise NotImplementedError('Repository root folder not found')
    with open(os.path.join(root, 'metrics.yml')) as fp:
        cfg = yaml.safe_load(fp)
        return cfg

def get_build_id():
    build_id = os.environ.get('BUILD_BUILDID')
    if build_id:
        return build_id
    raise NotImplementedError('Build ID info not found')

AZURE_PR_SOURCE_BRANCH_ENV = 'SYSTEM_PULLREQUEST_SOURCEBRANCH'

def is_pull_request():
    return AZURE_PR_SOURCE_BRANCH_ENV in os.environ

def get_source_branch():
    pr_branch = os.environ.get(AZURE_PR_SOURCE_BRANCH_ENV)
    if pr_branch:
        return pr_branch
    raise NotImplementedError('Source branch info not found')

def get_commit():
    commit = os.environ.get('BUILD_SOURCEVERSION')
    if commit:
        return commit
    raise NotImplementedError('Commit info not found')

class Metrics(object):
    def __init__(self) -> None:
        self.settings = get_settings()
        self.metrics = {}
    
    def put(self, name: str, value: float) -> None:
        self.metrics[name] = {
            "value": value
        }

    def publish(self):
        if not is_pull_request():
            print('Not a pull request, not submitting metrics')
            return
        client = pymongo.MongoClient(get_mongo_connection_string())
        db = client[self.settings['db']]
        coll = db[self.settings['collection']]
        coll.insert_one({
            "created": datetime.datetime.now(),
            "build_id": get_build_id(),
            "branch": get_source_branch(),
            "commit": get_commit(),
            "metrics": self.metrics
        })
