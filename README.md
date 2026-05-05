# agent_playground

Personal quant platform for A-share investing. Mixes:

- **Qlib** for offline factor research and PIT-correct backtesting.
- **baostock** for free daily-frequency price + fundamentals.
- **ops** (FastAPI) for live monitoring, persisted strategies, and
  multi-channel notifications.
- Future: QMT (via 国信 iQuant) for execution; text + LLM signals as
  a NLP-engineer differentiation point.

```
agent_playground/
├── common/   # Symbol, universe, calendar
├── data/     # Provider-agnostic market data
├── research/ # Qlib pipelines (isolated venv)
├── ops/      # FastAPI live service
└── data_storage/   # local cache, gitignored
```

See `CLAUDE.md` for architecture, commands, and current status.
