import yaml
import pymongo
import os
import sys
import matplotlib.pyplot as plt
import numpy as np

from pymetrics.env import get_env

plt.style.use('ggplot')


class Metrics(object):
  def __init__(self, env):
    self.client = pymongo.MongoClient(env.mongo_connection)
    db = self.client[env.mongo_db]
    self.col = db[env.mongo_collection]

  def all(self):
    return self.col.find()

  def last_for_branch(self, branch): 
    return next(self.col.find({'branch': branch}).sort([('created', pymongo.DESCENDING)]).limit(1))

  def bars(self, branch, reference):
    branch_metrics = self.last_for_branch(branch)['metrics']
    reference_metrics = self.last_for_branch(reference)['metrics']

    b = []
    r = []
    ticks = []
    for field in branch_metrics.keys() | reference_metrics.keys():
      b.append(branch_metrics.get(field, {}).get('value', 0))
      r.append(reference_metrics.get(field, {}).get('value', 0))
      ticks.append(field)

    return b, r, ticks

if __name__ == '__main__':
  os.makedirs('_pymetrics', exist_ok=True)
  env = get_env()
  m = Metrics(env)
  BRANCH = env.branch
  if env.is_pr:
    target_branch = env.target_branch
    print(f"Comparing {BRANCH} and {target_branch}")
    branch, main, ticks = m.bars(BRANCH, target_branch)
    fig, ax = plt.subplots()
    index = np.arange(len(ticks))
    bar_width = 0.35
    opacity = 0.9
    ax.bar(index, branch, bar_width, alpha=opacity, color='r',
          label=BRANCH)
    ax.bar(index+bar_width, main, bar_width, alpha=opacity, color='b',
          label=target_branch)
    ax.set_xlabel('Metrics')
    ax.set_ylabel('Value')
    ax.set_title(f"{BRANCH} vs {target_branch}")
    ax.set_xticks(index + bar_width / 2)
    ax.set_xticklabels(ticks)
    ax.legend()
    plt.savefig('_pymetrics/diff.png')
