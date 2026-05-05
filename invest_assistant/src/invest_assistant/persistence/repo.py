"""Mapping between Strategy domain objects and ORM rows."""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..strategies.base import Strategy, Triggered
from ..strategies.registry import lookup
from .models import EventRow, SignalStateRow, StrategyRow


# ── Strategy ─────────────────────────────────────────────────────────────────

def _row_to_strategy(row: StrategyRow) -> Strategy:
    cls = lookup(row.type)
    return cls.from_config(
        json.loads(row.config_json),
        strategy_id=row.strategy_id,
        name=row.name,
        market=row.market,
        channels=json.loads(row.channels),
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _strategy_to_row(s: Strategy, existing: StrategyRow | None = None) -> StrategyRow:
    if existing is None:
        existing = StrategyRow(strategy_id=s.strategy_id)
    existing.name        = s.name
    existing.type        = s.type_name()
    existing.config_json = json.dumps(s.to_config())
    existing.market      = s.market
    existing.channels    = json.dumps(s.channels)
    existing.is_active   = s.is_active
    return existing


def save_strategy(sess: Session, strategy: Strategy) -> None:
    existing = sess.get(StrategyRow, strategy.strategy_id)
    sess.add(_strategy_to_row(strategy, existing))


def get_strategy(sess: Session, strategy_id: str) -> Strategy | None:
    row = sess.get(StrategyRow, strategy_id)
    return _row_to_strategy(row) if row else None


def delete_strategy(sess: Session, strategy_id: str) -> bool:
    row = sess.get(StrategyRow, strategy_id)
    if row is None:
        return False
    sess.delete(row)
    return True


def list_active_strategies(sess: Session) -> list[Strategy]:
    rows = sess.scalars(
        select(StrategyRow).where(StrategyRow.is_active == True)
    ).all()
    return [_row_to_strategy(r) for r in rows]


def list_all_strategies(sess: Session) -> list[Strategy]:
    rows = sess.scalars(select(StrategyRow).order_by(StrategyRow.created_at)).all()
    return [_row_to_strategy(r) for r in rows]


# ── Event ────────────────────────────────────────────────────────────────────

def save_event(
    sess: Session,
    strategy_id: str,
    triggered: Triggered,
    asof: date,
    notified: bool = False,
) -> EventRow:
    row = EventRow(
        strategy_id=strategy_id,
        symbol=triggered.symbol,
        asof=asof,
        event_type=triggered.event_type,
        snapshot_json=json.dumps(triggered.snapshot, default=str),
        notified=notified,
        notified_at=datetime.now() if notified else None,
    )
    sess.add(row)
    return row


def list_events(
    sess: Session,
    strategy_id: str | None = None,
    limit: int = 100,
) -> list[EventRow]:
    stmt = select(EventRow).order_by(EventRow.triggered_at.desc()).limit(limit)
    if strategy_id is not None:
        stmt = stmt.where(EventRow.strategy_id == strategy_id)
    return list(sess.scalars(stmt).all())


# ── SignalState ──────────────────────────────────────────────────────────────

def get_signal_state(sess: Session, strategy_id: str) -> tuple[date, list[str]] | None:
    row = sess.get(SignalStateRow, strategy_id)
    if row is None:
        return None
    return row.asof, json.loads(row.snapshot_json)


def set_signal_state(
    sess: Session,
    strategy_id: str,
    asof: date,
    symbols: list[str],
) -> None:
    row = sess.get(SignalStateRow, strategy_id)
    payload = json.dumps(symbols)
    if row is None:
        sess.add(SignalStateRow(strategy_id=strategy_id, asof=asof, snapshot_json=payload))
    else:
        row.asof = asof
        row.snapshot_json = payload
