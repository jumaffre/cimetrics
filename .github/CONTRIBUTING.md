## Development

Clone the repository:

```sh
git clone git@github.com:jumaffre/cimetrics.git
cd cimetrics
```

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