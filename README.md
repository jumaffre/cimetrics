# cimetrics

[![Build Status](https://dev.azure.com/jumaffre/metrics-devops/_apis/build/status/jumaffre.metrics-devops?branchName=master)](https://dev.azure.com/jumaffre/metrics-devops/_build/latest?definitionId=1&branchName=master)
[![PyPI version](https://badge.fury.io/py/cimetrics.svg)](https://badge.fury.io/py/cimetrics)

`cimetrics` lets you track crucial metrics to avoid unwanted regressions. It is easy to integrate with your existing projects and automatically provides quick feedback in your GitHub Pull Requests. See it in action [here](https://github.com/jumaffre/cimetrics/pull/66#issuecomment-573324351).

<p align="center"> <img src="https://raw.githubusercontent.com/jumaffre/cimetrics/cimetrics/cimetrics/image2020-01-11%2015%3A03%3A37.764906.png" width="600"></p>

## Install

```sh
pip install cimetrics
```

## Using cimetrics

### Setup storage

Metrics data are stored by in any MongoDB-compatible database.

An easy way to get storage set up is to spin up a [Cosmos DB](https://docs.microsoft.com/en-us/azure/cosmos-db/introduction) instance in Azure. The connection string should be stored as the `METRICS_MONGO_CONNECTION` secret variable in your CI system.

### Pushing metrics from your tests

You can use the simple python API to push your metrics to your storage:

```python
import cimetrics.upload

with cimetrics.upload.Metrics() as metrics:
  # Run some tests and collect some data
  metrics.put("metric1 name (unit)", metric_1)
  metrics.put("metric2 name (unit)", metric_2)
```

Note that `metric_1` and `metric_2` must be instances of [numbers.Real](https://docs.python.org/3.7/library/numbers.html#numbers.Real), for example `float` or `int`.

### Setup the CI

Your CI is responsible for rendering the metrics report and posting them to your Pull Requests in GitHub. For this, you should create a [personal authentication token](https://help.github.com/en/articles/creating-a-personal-access-token-for-the-command-line) with Write access to the repository for the account you want to post on behalf of `cimetrics`. Then, you should set up the token as the `GITHUB_TOKEN` secret variable in your CI system. Don't forget to add that user as a personal contributor (Write access) to your Github repository as well.

Then, you should add the following steps to your CI configuration file, e.g. for Azure Pipelines:

```yaml
# Your application. This step collects and uploads your metrics
# to your MongoDB instance.
- script: python app/main.py
  env:
    METRICS_MONGO_CONNECTION: $(METRICS_MONGO_CONNECTION)
  displayName: 'Run app and collect metrics'

# This step generates a graph reporting the differences between
# your branch and the target branch.
# Only run on Pull Requests build.
- script: python -m cimetrics.plot
  env:
    METRICS_MONGO_CONNECTION: $(METRICS_MONGO_CONNECTION)
  displayName: 'Plot metrics'
  condition: eq(variables['Build.Reason'], 'PullRequest')

# This step publishes a report comment on the GitHub Pull Request
# using GITHUB_TOKEN as authentication (use secret variables!)
# Only run on Pull Requests build.
- script: python -m cimetrics.github_pr
  env:
    GITHUB_TOKEN: $(GITHUB_TOKEN)
  displayName: 'Post metrics graphs as PR comment'
  condition: eq(variables['Build.Reason'], 'PullRequest')
```

See [azure-pipelines.yml](https://github.com/jumaffre/cimetrics/blob/master/azure-pipelines.yml) for a full working example.

### Create the `metrics.yml` file

The last step is to create a new `metrics.yml` configuration file at the root of your repository. The file should specify the name of the database and collection used for MongoDB. For example:

```yaml
db: 'metrics'
collection: 'metrics_performance'
view: 'trend'
```

That's it! The next time you create a Pull Request, your CI will automatically store your metrics and publish a graph comparing your metrics against the same metrics on the branch you are merging to. Note that the cimetrics PR comment is updated for each subsequent build.

## Caveats

- If the CI has never run on the target branch (e.g. `master` - likely to happen when you first set up `cimetrics`), the report will only show the values that have been uploaded, without any comparison.
- The rendered images are currently hosted in the target GitHub repository itself, under the `cimetrics` branch, in the `cimetrics` directory.

## Supported CI pipelines

CI Metrics currently supports [Azure Pipelines](https://azure.microsoft.com/en-us/services/devops/pipelines/), but it should be very easy to add support for other build pipelines by [subclassing GitEnv](https://github.com/jumaffre/cimetrics/blob/master/cimetrics/env.py#L72) and providing the right attributes.
