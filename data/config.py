"""Data layer configuration — paths to local cache.

Default location: agent_playground/data_storage/. Override via env var
`AGENT_DATA_ROOT` if needed.
"""
import os
from pathlib import Path


_DEFAULT_ROOT = Path(__file__).resolve().parent.parent / "data_storage"
DATA_ROOT = Path(os.environ.get("AGENT_DATA_ROOT", str(_DEFAULT_ROOT)))

BAOSTOCK_DATA_DIR = DATA_ROOT / "baostock"
DB_PATH = BAOSTOCK_DATA_DIR / "cache.db"

DATA_ROOT.mkdir(parents=True, exist_ok=True)
BAOSTOCK_DATA_DIR.mkdir(parents=True, exist_ok=True)
