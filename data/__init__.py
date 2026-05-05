"""Market data layer.

Public interface lives in `data.api`. Provider-specific implementations
live under `data.providers`. Both `ops/` (live monitoring) and
`research/` (offline backtesting) consume from this package.
"""
