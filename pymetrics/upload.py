import os
import sys
import datetime
import pymongo

ENV_METRICS_PROJECT = 'METRICS_PROJECT'
ENV_METRICS_MONGO_CONNECTION = 'METRICS_MONGO_CONNECTION'

# For now, only Azure Pipeline's environment variables are supported.

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
    def __init__(self, project=None) -> None:
        if project:
            self.project = project
        else:
            self.project = os.environ[ENV_METRICS_PROJECT]
        self.metrics = {}
    
    def put(self, name: str, value: float) -> None:
        self.metrics[name] = {
            "value": value
        }

    def publish(self):
        if not is_pull_request():
            print('Not a pull request, not submitting metrics')
            return
        client = pymongo.MongoClient(os.environ[ENV_METRICS_MONGO_CONNECTION])
        db = client.metrics
        coll = db['metrics_' + self.project]
        coll.insert_one({
            "created": datetime.datetime.now(),
            "build_id": get_build_id(),
            "branch": get_source_branch(),
            "commit": get_commit(),
            "metrics": self.metrics
        })
