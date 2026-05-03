# agent_playground — Personal Quant Platform

## Monorepo structure

```
agent_playground/
├── invest_assistant/   # FastAPI service: monitoring engine + notifications
└── qlib_research/      # Qlib factor research + backtesting (separate venv)
```

Data lives at `../data/` (sibling to this repo, outside git):
- `data/baostock/cache.db` — SQLite cache for stocks + financial metrics
- `data/my/`              — app DB (monitor rules, events)

---

## invest_assistant

**Purpose:** Runs as a background service. Checks user-defined monitor rules
against A-share fundamental data every hour during market hours, sends
Email/Telegram notifications when conditions trigger.

### Tech stack
- FastAPI + APScheduler (hourly jobs, 16:30 after-close check)
- baostock — A-share data (free, ~5200 stocks)
- SQLite — local cache for bulk financial metrics (avoid per-stock API calls)
- Pydantic v2 / pydantic-settings

### Key files
| Path | Role |
|------|------|
| `src/invest_assistant/providers/baostock.py` | Query layer — reads from SQLite cache |
| `src/invest_assistant/providers/sync.py` | Sync layer — downloads from baostock API into cache |
| `src/invest_assistant/core/monitor/engine.py` | MonitorEngine — evaluates rules, fires notifications |
| `src/invest_assistant/services/screener.py` | StockScreener — convenience wrapper around query_all_financial_metrics |
| `src/invest_assistant/config.py` | Settings (paths, notification toggles) |

### Data flow
```
sync_stock_meta()       → stocks table (~5200 rows, seconds)
sync_financial_data()   → financial_metrics table (~20 min for all stocks)
                               ↓
query_all_financial_metrics()  ← screener / monitor engine read from cache
query_daily_kdata()            ← baostock on-demand per stock (fast)
```

### Financial metrics — units
baostock returns ratios as decimals; we store as **percentages**:
- `roe`: 10.5 = 10.5%
- `gross_margin`: 89.8 = 89.8%
- `debt_to_asset_ratio`: 12.1 = 12.1%
- `pe_ttm`, `pb`: raw multiples, no conversion

`revenue_yoy` and `net_income_yoy` are deferred (NaN in Phase 1).

### Running
```bash
cd invest_assistant
pip install -r requirements.txt
# First time: populate cache
python -c "from src.invest_assistant.providers.sync import sync_stock_meta, sync_financial_data; sync_stock_meta(); sync_financial_data()"
# Start service
uvicorn src.invest_assistant.main:app --reload
```

---

## qlib_research

**Purpose:** Offline factor research and PIT-correct backtesting.
Separate venv to avoid dependency conflicts with invest_assistant.

```bash
cd qlib_research
source venv/bin/activate
python validate.py   # smoke test (Phase 0, already passed)
```

---

## Overall architecture

```
baostock (data source)
  → invest_assistant/providers/ (cache + query layer)
    → invest_assistant (monitoring + notifications)
      → QMT / XtQuant (live execution, Phase 4)

baostock (data source)
  → qlib_research/ (factor research + ML backtest)
    → parquet signal files
      → invest_assistant MonitorEngine SignalRule (Phase 3)
```

---

## Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| 0 | ✅ done | Qlib + baostock toolchain validated |
| 1 | ✅ done | providers/ migrated from zvt → baostock |
| 2 | next | Qlib research pipeline (factors, LightGBM, PIT backtest) |
| 3 | later | Wire Qlib parquet signals into MonitorEngine |
| 4 | 3-6 mo | QMT simulation → live trading |

## Known decisions / gotchas

- **provider.py** (`providers/provider.py`) is the old zvt implementation — superseded by `baostock.py`, safe to delete once comfortable
- **HK stocks**: baostock doesn't support HK; add AKShare/Tushare Pro via providers/ abstraction when needed
- **revenue_yoy / net_income_yoy**: need two consecutive quarters of `MBRevenue`/`netProfit` from baostock; deferred to Phase 2
- **Qlib venv isolation**: Qlib has dependency conflicts with some libs; always use `qlib_research/venv`, exchange data via parquet files
- **T+1 execution**: signals generated at close → execute at next day's open price (use `deal_price="open"` in Qlib executor)
- **PIT data**: Qlib supports point-in-time financial data via `announce_date`; requires financial data with pubDate column to avoid look-ahead bias
