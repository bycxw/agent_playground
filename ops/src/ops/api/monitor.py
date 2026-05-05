"""Strategy + monitoring API."""
from __future__ import annotations

import json
from datetime import date as _date
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..core.monitor import check_all, check_strategy
from ..persistence import session
from ..persistence import repo
from ..strategies import known_types, lookup
from ..strategies.base import Strategy

router = APIRouter(prefix="/strategies", tags=["strategies"])


# ── DTOs ─────────────────────────────────────────────────────────────────────

class StrategyCreate(BaseModel):
    name: str
    type: str = Field(..., description=f"One of: {known_types()}")
    config: dict[str, Any]
    market: str = "A股"
    channels: list[str] = []


class StrategyOut(BaseModel):
    strategy_id: str
    name: str
    type: str
    config: dict[str, Any]
    market: str
    channels: list[str]
    is_active: bool


class TriggeredOut(BaseModel):
    symbol: str
    name: str
    snapshot: dict[str, Any]
    event_type: str


class CheckResult(BaseModel):
    strategy_id: str
    strategy_name: str
    triggered_count: int
    triggered: list[TriggeredOut]


class EventOut(BaseModel):
    event_id: int
    strategy_id: str
    symbol: str
    asof: _date
    event_type: str
    snapshot: dict[str, Any]
    notified: bool


# ── Helpers ──────────────────────────────────────────────────────────────────

def _to_out(s: Strategy) -> StrategyOut:
    return StrategyOut(
        strategy_id=s.strategy_id,
        name=s.name,
        type=s.type_name(),
        config=s.to_config(),
        market=s.market,
        channels=s.channels,
        is_active=s.is_active,
    )


# ── Routes: strategies CRUD ─────────────────────────────────────────────────

@router.get("", response_model=list[StrategyOut])
async def list_strategies():
    with session() as sess:
        return [_to_out(s) for s in repo.list_all_strategies(sess)]


@router.post("", response_model=StrategyOut, status_code=201)
async def create_strategy(req: StrategyCreate):
    try:
        cls = lookup(req.type)
    except KeyError:
        raise HTTPException(400, f"Unknown strategy type {req.type!r}; "
                                 f"known: {known_types()}")

    try:
        strategy = cls.from_config(
            req.config,
            name=req.name,
            market=req.market,
            channels=req.channels,
        )
    except (TypeError, ValueError) as e:
        raise HTTPException(400, f"Invalid strategy config: {e}")

    with session() as sess:
        repo.save_strategy(sess, strategy)
    return _to_out(strategy)


@router.get("/{strategy_id}", response_model=StrategyOut)
async def get_strategy_route(strategy_id: str):
    with session() as sess:
        s = repo.get_strategy(sess, strategy_id)
    if s is None:
        raise HTTPException(404, "Strategy not found")
    return _to_out(s)


@router.delete("/{strategy_id}", status_code=204)
async def delete_strategy_route(strategy_id: str):
    with session() as sess:
        deleted = repo.delete_strategy(sess, strategy_id)
    if not deleted:
        raise HTTPException(404, "Strategy not found")


# ── Routes: check + events ──────────────────────────────────────────────────

@router.post("/check", response_model=list[CheckResult])
async def check_strategies(strategy_id: Optional[str] = None):
    """Trigger evaluation for one strategy or all active ones."""
    if strategy_id:
        triggered = check_strategy(strategy_id)
        with session() as sess:
            s = repo.get_strategy(sess, strategy_id)
        results = {strategy_id: (s, triggered)} if s else {}
    else:
        all_results = check_all()
        with session() as sess:
            strategies = {s.strategy_id: s for s in repo.list_active_strategies(sess)}
        results = {sid: (strategies.get(sid), tr) for sid, tr in all_results.items()
                   if strategies.get(sid)}

    return [
        CheckResult(
            strategy_id=sid,
            strategy_name=s.name,
            triggered_count=len(tr),
            triggered=[
                TriggeredOut(symbol=t.symbol, name=t.name,
                             snapshot=t.snapshot, event_type=t.event_type)
                for t in tr[:50]
            ],
        )
        for sid, (s, tr) in results.items()
    ]


@router.get("/events", response_model=list[EventOut])
async def list_events(strategy_id: Optional[str] = None, limit: int = 100):
    with session() as sess:
        rows = repo.list_events(sess, strategy_id=strategy_id, limit=limit)
        return [
            EventOut(
                event_id=r.event_id,
                strategy_id=r.strategy_id,
                symbol=r.symbol,
                asof=r.asof,
                event_type=r.event_type,
                snapshot=json.loads(r.snapshot_json),
                notified=r.notified,
            )
            for r in rows
        ]
