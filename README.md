# agent_playground

Personal quant platform. A-share is the first market; HK ahead via the
provider abstraction. Mixes:

- **Qlib** for offline factor research and PIT-correct backtesting.
- **baostock** for free A-share daily prices + fundamentals (HK/US slot
  in via `data.providers.*` when needed).
- **ops** (FastAPI) for live monitoring, persisted strategies, and
  multi-channel notifications.
- Future: QMT (via 国信 iQuant) for execution; text + LLM signals as
  a NLP-engineer differentiation point.

```
agent_playground/
├── common/   # Symbol (multi-market: SH/SZ/HK), universe, calendar
├── data/     # Provider-agnostic market data
├── research/ # Qlib pipelines (isolated venv)
├── ops/      # FastAPI live service
└── data_storage/   # local cache, gitignored
```

See `CLAUDE.md` for architecture, commands, and current status.
