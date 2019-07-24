# cimetrics

[![Build Status](https://dev.azure.com/jumaffre/metrics-devops/_apis/build/status/jumaffre.metrics-devops?branchName=master)](https://dev.azure.com/jumaffre/metrics-devops/_build/latest?definitionId=1&branchName=master)

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

## Storage

CI Metrics can store data in any MongoDB-compatible database.

An easy way to get storage set up for CI Metrics is to spin up a [Cosmos DB](https://docs.microsoft.com/en-us/azure/cosmos-db/introduction) in Azure. The connection string can be stored as a secret variable in the CI system.

## Supported CI pipelines

CI Metrics currently supports [Azure Pipelines](https://azure.microsoft.com/en-us/services/devops/pipelines/), but it should be very easy to add support for other build pipelines by [subclassing GitEnv](https://github.com/jumaffre/cimetrics/blob/master/cimetrics/env.py#L72) and providing the right attributes.
