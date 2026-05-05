# research

Offline factor research — currently Qlib-based. Lives in its own venv
because Qlib has dependency conflicts with the rest of the workspace.

## Setup

The venv is gitignored. Recreate after cloning or after a rename:

```bash
cd research
python -m venv venv
source venv/bin/activate
pip install -e ../        # common + data, so research consumes our cache
pip install qlib baostock lightgbm pyarrow

# One-time: download Qlib's bundled cn_data (price/volume only, ends 2021-06-11)
python -c "
from qlib.tests.data import GetData
GetData().qlib_data(name='qlib_data_simple', target_dir='~/.qlib/qlib_data/cn_data',
                    region='cn', interval='1d', exists_skip=True)
"
```

## Pipelines

- `pipeline.py` — Phase 2 LightGBM + Alpha158 on CSI300, T+1 open
  execution, real trading costs. Outputs `signals/daily.parquet`.

## Output contract

`signals/daily.parquet` is the contract between research and ops:

| column   | type             | notes                                |
|----------|------------------|--------------------------------------|
| date     | datetime64[ns]   | asof date the score is for           |
| symbol   | str              | canonical "SH600000"                 |
| score    | float64          | predicted forward return             |
| rank     | int64            | 1 = highest predicted return per day |

`ops/strategies/signal_topk.py` (Phase 3) consumes this file directly.
