import yaml
import pymongo
import os
import matplotlib.pyplot as plt
import numpy as np
plt.style.use('ggplot')

def get_mongo_connection_string():
  return os.environ['METRICS_MONGO_CONNECTION']

def get_settings():
  root = os.getenv('BUILD_SOURCEDIRECTORY')
  if not root:
    raise NotImplementedError('Repository root folder not found')
  with open(os.path.join(root, 'metrics.yml')) as fp:
    cfg = yaml.safe_load(fp)
    return cfg

def get_branch():
  branch = os.environ.get('BUILD_SOURCEBRANCH')
  if branch:
    return branch
  raise NotImplementedError('Source branch info not found')

CFG = get_settings()

class Metrics:
  def __init__(self):
    uri = get_mongo_connection_string()
    self.client = pymongo.MongoClient(uri)
    db = self.client[CFG['db']]
    self.col = db[CFG['collection']]

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
  m = Metrics()
  BRANCH = get_branch()
  branch, main, ticks = m.bars(BRANCH, CFG['main_branch'])
  fig, ax = plt.subplots()
  index = np.arange(len(ticks))
  bar_width = 0.35
  opacity = 0.9
  ax.bar(index, branch, bar_width, alpha=opacity, color='r',
         label=BRANCH)
  ax.bar(index+bar_width, main, bar_width, alpha=opacity, color='b',
         label=CFG['main_branch'])
  ax.set_xlabel('Metrics')
  ax.set_ylabel('Value')
  ax.set_title(f"{BRANCH} vs {CFG['main_branch']}")
  ax.set_xticks(index + bar_width / 2)
  ax.set_xticklabels(ticks)
  ax.legend()
  plt.savefig('_pymetrics/diff.png')
