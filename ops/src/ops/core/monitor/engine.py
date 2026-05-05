"""Monitor engine — loads strategies from DB, evaluates them, dispatches notifications.

The engine is intentionally stateless: every call hits the DB for the
current set of active strategies. This keeps the live service and any
ad-hoc scripts on the same source of truth.
"""
from __future__ import annotations

import logging
from datetime import date

from ...notification import dispatch
from ...persistence import repo, session
from ...strategies.base import Strategy, Triggered

logger = logging.getLogger(__name__)


def _evaluate_and_record(s: Strategy, asof: date) -> list[Triggered]:
    """Evaluate one strategy, persist triggered events, dispatch notifications."""
    try:
        triggered = s.evaluate(asof)
    except Exception:
        logger.exception("Strategy %s (%s) failed to evaluate", s.name, s.strategy_id)
        return []

    if not triggered:
        return []

    notify = bool(s.channels)
    with session() as sess:
        for t in triggered:
            repo.save_event(sess, s.strategy_id, t, asof, notified=notify)

    if notify:
        dispatch(s.name, triggered, s.channels)

    logger.info("Strategy %s: %d triggered", s.name, len(triggered))
    return triggered


def check_all(asof: date | None = None) -> dict[str, list[Triggered]]:
    """Run every active strategy. Returns {strategy_id: [Triggered...]}."""
    asof = asof or date.today()
    with session() as sess:
        strategies = repo.list_active_strategies(sess)

    return {s.strategy_id: _evaluate_and_record(s, asof) for s in strategies}


def check_strategy(strategy_id: str, asof: date | None = None) -> list[Triggered]:
    """Run a single strategy by id. Returns [] if missing or inactive."""
    asof = asof or date.today()
    with session() as sess:
        s = repo.get_strategy(sess, strategy_id)
    if s is None:
        logger.warning("Strategy not found: %s", strategy_id)
        return []
    if not s.is_active:
        logger.info("Strategy %s is inactive, skipping", s.name)
        return []
    return _evaluate_and_record(s, asof)
