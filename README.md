# metrics-devops

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
python -m pymetrics.plot
ls _pymetrics
```


