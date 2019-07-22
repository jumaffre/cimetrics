import yaml
import pymongo
import os
import matplotlib.pyplot as plt
import numpy as np
plt.style.use('ggplot')

def get_settings():
  with open('metrics.yml') as cfgf:
    cfg = yaml.safe_load(cfgf)
    return cfg['db'], cfg['collection'], cfg['main_branch']

DB, COLLECTION, MAIN_BRANCH = get_settings()

class Metrics:
  def __init__(self):
    uri = os.getenv("COSMOS_CONNECTION")
    self.client = pymongo.MongoClient(uri)
    db = self.client[DB]
    self.col = db[COLLECTION]

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
  BRANCH = 'foo'
  branch, main, ticks = m.bars(BRANCH, MAIN_BRANCH)
  fig, ax = plt.subplots()
  index = np.arange(len(ticks))
  bar_width = 0.35
  opacity = 0.9
  ax.bar(index, branch, bar_width, alpha=opacity, color='r',
         label=BRANCH)
  ax.bar(index+bar_width, main, bar_width, alpha=opacity, color='b',
         label=MAIN_BRANCH)
  ax.set_xlabel('Metrics')
  ax.set_ylabel('Value')
  ax.set_title(f'{BRANCH} vs {MAIN_BRANCH}')
  ax.set_xticks(index + bar_width / 2)
  ax.set_xticklabels(ticks)
  ax.legend()
  plt.savefig('diff.png')
