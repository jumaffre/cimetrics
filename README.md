# cimetrics 

[![Build Status](https://dev.azure.com/jumaffre/metrics-devops/_apis/build/status/jumaffre.metrics-devops?branchName=master)](https://dev.azure.com/jumaffre/metrics-devops/_build/latest?definitionId=1&branchName=master)

`cimetrics` lets you track crucial metrics to avoid unwanted regressions. It is easy to integrate with your existing projects and automatically provides quick feedback in your GitHub Pull Requests.

## Development

Install as editable/dev package:
```sh
pip install -e .
```

Submit sample metrics and create plots:
```sh
export METRICS_MONGO_CONNECTION=...
python app/main.py
python -m cimetrics.plot
ls _cimetrics
```

## Using cimetrics in your own project

### Setup storage

Metrics data are stored by in any MongoDB-compatible database.

An easy way to get storage set up is to spin up a [Cosmos DB](https://docs.microsoft.com/en-us/azure/cosmos-db/introduction) instance in Azure. The connection string should be stored as the `METRICS_MONGO_CONNECTION` secret variable in your CI system.

### Pushing metrics from your tests

You can use the simple python API to push your metrics to your storage. First, make sure to install the `cimetrics` python module (for example, by running `pip install cimetrics` or adding `cimetrics` to your `requirements.txt`). Once this is done, you will be able to write:

```python
import cimetrics.upload

metrics = cimetrics.upload.Metrics()

# Run some tests and collect some data

metrics.put("metric1 name (unit)", metric_1)
metrics.put("metric2 name (unit)", metric_2)

metrics.publish()
```

Note that `metric_1` and `metric_2` should _not_ be string but integer or float.

### Setup the CI

Your CI is responsible for rendering the metrics report and posting them to your Pull Requests in GitHub. For this, you should create a [personal authentication token](https://help.github.com/en/articles/creating-a-personal-access-token-for-the-command-line) with Write access to the repository for the account you want to post on behalf of `cimetrics`. Then, you should set up the token as the `GITHUB_TOKEN` secret variable in your CI system. Don't forget to add that user as a personal contributor (Write access) to your Github repository as well.

Then, you should add the following steps to your CI configuration file, e.g. for Azure Pipelines:

```yaml
# Plot the metrics on the branch against the target branch (e.g. master)
- script: python -m cimetrics.plot
  env:
    METRICS_MONGO_CONNECTION: $(METRICS_MONGO_CONNECTION)
  displayName: 'Plot cimetrics'

# Publish the rendered plot on the Github PR
# (only run for builds triggered by Pull Requests)
- script: python -m cimetrics.github_pr
  env:
    GITHUB_TOKEN: $(GITHUB_TOKEN)
  displayName: 'Post cimetrics graphs as PR comment'
  condition: eq(variables['Build.Reason'], 'PullRequest')

# Publish plot as a build artifact (optional)
- task: PublishBuildArtifacts@1
  inputs:
    pathtoPublish: _cimetrics
    artifactName: cimetrics
  displayName: 'Publish cimetrics graphs as build artifact'
```

See [azure-pipelines.yml](https://github.com/jumaffre/cimetrics/blob/master/azure-pipelines.yml) for a full working example.

### Create the `metrics.yml` file

The last step is to create a new `metrics.yml` configuration file at the root of your repository. The file should specify the name of the database and collection used for MongoDB. For example:

```yaml
db: 'metrics'
collection: 'metrics_performance'
```

That's it! The next time you create a Pull Request, your CI will automatically store your metrics and publish a graph comparing your metrics against the same metrics on the branch you are merging to.

## Caveats

- If the CI has never run on the target branch (e.g. `master` - likely to happen when you first set up `cimetrics`), the report will show the metrics results of the branch to merge against itself. It will be displayed fine once the CI has run on the target branch.
- The rendered images are currently hosted in the target GitHub repository itself, under the `cimetrics` branch, in the `cimetrics` directory.

## to-do

- [x] Publish to PyPi (https://pypi.org/project/cimetrics/)
- [ ] Use a GitHub bot instead of tokens
- [ ] Improve plotting (standard deviation, etc.)
- [ ] Add personalised PR message

## Supported CI pipelines

CI Metrics currently supports [Azure Pipelines](https://azure.microsoft.com/en-us/services/devops/pipelines/), but it should be very easy to add support for other build pipelines by [subclassing GitEnv](https://github.com/jumaffre/cimetrics/blob/master/cimetrics/env.py#L72) and providing the right attributes.

