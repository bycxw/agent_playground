# agent_playground — Personal Quant Platform

## Layout

```
agent_playground/
├── common/         # Cross-module shared types (Symbol, calendar, universe)
├── data/           # Market data layer (provider-agnostic API + baostock)
├── research/       # Offline factor research (Qlib pipelines, isolated venv)
├── ops/            # FastAPI service: monitoring, notifications, execution
├── data_storage/   # Local cache (gitignored, sibling to packages)
└── pyproject.toml  # Top-level workspace install
```

`data_storage/` lives outside the source tree so packages can be cleanly
installed without picking up cache/db files. Override its location via
`AGENT_DATA_ROOT` env var; default is `agent_playground/data_storage/`.

---

## Packages

### common/

`Symbol` — canonical stock identifier. One type, five accepted formats.

```python
from common.symbols import Symbol

s = Symbol.parse("600000.SH")     # also accepts "SH600000", "sh.600000",
                                  # "sh600000", "stock_sh_600000"
s.canonical()  # "SH600000"  ← DB primary key, signal parquet
s.baostock()   # "sh.600000" ← baostock API
s.qlib()       # "sh600000"  ← qlib internal
s.display()    # "600000.SH" ← human-readable
```

### data/

Public surface in `data.api` (PIT-aware signatures, work in progress).
Legacy baostock query/sync functions re-exported from `data` for now.

```python
from data import query_stock_list, query_all_financial_metrics, sync_stock_meta
```

- `data.providers.baostock`     — baostock query layer
- `data.providers.baostock_sync`— baostock sync layer (writes SQLite cache)
- `data.config`                 — `DB_PATH`, `BAOSTOCK_DATA_DIR`
- `data.text/`                  — placeholder for LLM/RAG text layer
- `data.store/`                 — placeholder for vector store + LLM cache

Database schema (PK = canonical symbol, no entity_id):

```sql
CREATE TABLE stocks            (symbol PK, code, exchange, name, updated_at);
CREATE TABLE financial_metrics (symbol PK, report_date, pe_ttm, pb, roe,
                                gross_margin, debt_to_asset_ratio, updated_at);
CREATE TABLE daily_kdata       (symbol+trade_date PK, open, high, low, close,
                                volume, amount);
```

Financial metrics are stored as **percentages** (roe=10.5 means 10.5%);
baostock returns decimals so sync multiplies by 100.

### research/

Renamed from `qlib_research/`. Isolated venv (Qlib has dependency
conflicts with the rest). Recreate after pulling:

```bash
cd research
python -m venv venv
source venv/bin/activate
pip install -e ../  ../ops  qlib baostock lightgbm pyarrow
python pipeline.py   # Phase 2 LightGBM + Alpha158 + backtest
```

Output: `research/signals/daily.parquet` (date, symbol, score, rank).
Symbol is canonical (`SH600000`), aligning with the rest of the system.

### ops/

FastAPI live monitoring service. Renamed from `invest_assistant/`.

| Path | Role |
|------|------|
| `src/ops/strategies/` | Strategy ABC + concrete subclasses (factor_rule today; signal_topk, llm_score, agent ahead) |
| `src/ops/persistence/` | SQLAlchemy ORM (strategies, events, signal_state) |
| `src/ops/notification/` | Channel ABC + email + telegram |
| `src/ops/core/monitor/engine.py` | `check_all(asof)`, `check_strategy(id, asof)` |
| `src/ops/api/` | HTTP routes (FastAPI) |
| `src/ops/main.py` | App entry, scheduler, lifespan |

Strategy types live in `ops.strategies` and self-register via the
`@register` decorator. Persistence stores them polymorphically as
`(type, config_json)` rows; `repo.get_strategy()` deserialises by
looking up the type in the registry.

```python
from ops.strategies import FactorRuleStrategy, Condition
from ops.persistence import session, repo
from ops.core.monitor import check_strategy

s = FactorRuleStrategy(
    name="value rule",
    market="A股",
    channels=["email", "telegram"],
    conditions=[Condition("pe_ttm", "<", 15), Condition("roe", ">", 10)],
)
with session() as sess:
    repo.save_strategy(sess, s)

triggered = check_strategy(s.strategy_id)
```

Notifications: each strategy declares `channels: list[str]`; engine
dispatches via the registered NotificationChannel for each name.

---

## Data flow

```
baostock ─┐
          ├→ data/  (cache)
akshare? ─┘
              │
          ┌───┴────┐
          ↓        ↓
      research/  ops/strategies (FactorRuleStrategy now;
      pipelines  SignalTopKStrategy in Phase 3 reads ←─┐
      (Qlib)         research/signals/daily.parquet)   │
          │                  │                          │
          ↓                  ↓                          │
      signals/        ops/core/monitor                  │
      daily.parquet   evaluate + persist + dispatch ────┘
                              │
                              ↓
                       NotificationChannel
                       (email / telegram / future webhook)
                              │
                              ↓
                       ops/execution (Phase 4: QMT)
```

---

## Setup

```bash
# Workspace install (common + data accessible everywhere)
pip install -e .

# ops service
pip install -e ./ops

# First-time data sync
python -c "from data import sync_stock_meta; sync_stock_meta()"
python -c "from data import sync_financial_data; sync_financial_data()"  # ~20 min

# Run service
uvicorn ops.main:app --reload

# Tests
python -m pytest common/tests/ ops/tests/
```

---

## Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| 0 | ✅ done | Qlib + baostock toolchain validated |
| 1 | ✅ done | Data layer migrated from zvt → baostock |
| 2 | ✅ done | LightGBM Alpha158 pipeline; signals/daily.parquet emits |
| Refactor | ✅ done | common/data/ops/research split, Strategy/persistence framework |
| 3 | next | SignalTopKStrategy reading research/signals/daily.parquet |
| 4 | 3-6 mo | QMT live execution (国信 iQuant 0-门槛 path) |

---

## Architectural decisions worth remembering

- **Symbol is the only correct identifier** — never store `entity_id`,
  `bs_code`, raw `code`+`exchange`. Canonical form `SH600000` is the
  DB primary key everywhere; Symbol class handles all conversions.
- **PIT-aware everywhere**: data API takes `asof: date`; financial
  pubDate must be respected when adding fundamental factors;
  research/text layer (future) requires strict pub_date filtering.
- **Strategy is polymorphic**: FactorRuleStrategy today; new types are
  one new module + `@register` away. The engine and persistence layer
  never need updating.
- **Channels decouple notification from strategy logic**. Adding
  DingTalk or a webhook is one new module.
- **Don't reinvent**: backtest_daily for backtesting (use Qlib),
  XtQuant API for execution (Phase 4 via QMT/国信 iQuant 0-门槛),
  Alpha158/360 as factor baseline.
- **Personal-quant differentiation lives in NLP/text**: build Chinese
  PIT announcement corpus + fine-tune FinGPT — that's the gap, not
  reimplementing momentum factors.

## Verifications done (still trustworthy after refactor)

- Qlib `csi300` instrument set is **PIT** at runtime (verified
  2026-05-05): instruments membership differs across asof dates,
  reflecting CSI300 historical reconstitutions. Phase 2's +22.3%
  excess return is not from universe survivorship bias.

## Known gaps / open

- Phase 3 not yet wired (SignalTopKStrategy reading parquet).
- `data.api` PIT-aware functions are signatures-only; need filling in
  before research can drop the Qlib cn_data dependency.
- `research/venv` must be recreated after rename (it's gitignored).
- `data.text/` and `data.store/{vector,llm_cache}` are placeholder
  packages — Tier 1+ LLM work picks them up.
