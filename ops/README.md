# ops

Live monitoring + notification + (future) execution service for the
personal quant platform.

## What it does

- Holds **strategies** (factor rules today; Top-K signal rules and LLM
  scorers ahead) in SQLite via SQLAlchemy.
- On schedule (or manual `POST /strategies/check`), evaluates each active
  strategy against the cached data layer.
- Dispatches Triggered events to the channels each strategy declares
  (email, telegram, …).
- Persists every event for audit/history.

Markets: A-share (SH/SZ) today via baostock; HK joins once a provider
that covers it (akshare / tushare) lands in `data/providers/`. Strategy
code uses canonical `Symbol` so adding HK is a data-layer concern only.

## Quick start

```bash
# from repo root
pip install -e .          # common + data
pip install -e ./ops

# first-time data sync (run from anywhere)
python -c "from data import sync_stock_meta; sync_stock_meta()"
python -c "from data import sync_financial_data; sync_financial_data()"  # ~20 min

# service
uvicorn ops.main:app --reload
# open http://localhost:8000/docs
```

## Adding a strategy type

1. New module under `src/ops/strategies/` subclassing `Strategy`. Implement
   `evaluate(asof)`, `to_config()`, `from_config()`, `type_name()`.
2. Decorate the class with `@register`.
3. Import it from `ops/strategies/__init__.py` so the registry picks it up.

That's it — persistence, API, and engine pick it up via the registry.

## Adding a notification channel

1. New module under `src/ops/notification/`, subclass `NotificationChannel`,
   implement `send(strategy_name, triggered)`.
2. Register it in `notification/__init__.py` (gated on a settings
   flag if it needs config).

## Layout

```
ops/
├── pyproject.toml
└── src/ops/
    ├── api/            FastAPI routes (strategies, stocks, sync)
    ├── core/monitor/   engine.py: check_all / check_strategy
    ├── notification/   channel.py + email.py + telegram.py + formatter.py
    ├── persistence/    SQLAlchemy ORM (strategies, events, signal_state)
    ├── strategies/     base.py, registry.py, factor_rule.py
    ├── config.py
    └── main.py
```

## Example: create a strategy via API

```bash
curl -X POST http://localhost:8000/api/v1/strategies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "低估价值股",
    "type": "factor_rule",
    "market": "A股",
    "channels": ["email"],
    "config": {
      "conditions": [
        {"field": "pe_ttm", "op": "<", "value": 15},
        {"field": "roe",    "op": ">", "value": 10}
      ],
      "condition_logic": "AND"
    }
  }'

# Trigger evaluation
curl -X POST http://localhost:8000/api/v1/strategies/check
```
