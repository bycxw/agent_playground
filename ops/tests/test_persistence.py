"""Round-trip tests for persistence/repo — strategy and event serialisation.

Uses an in-memory SQLite via DATABASE_URL_OVERRIDE so we don't touch the
real ops.db.
"""
import os
from datetime import date

import pytest

# Override the DB before importing anything that touches persistence.
os.environ["DATABASE_URL_OVERRIDE"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ops.persistence import models, repo
from ops.strategies import Condition, FactorRuleStrategy, Triggered


@pytest.fixture
def sess():
    """Fresh in-memory SQLite session per test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    models.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as s:
        yield s


def _make_strategy(**overrides) -> FactorRuleStrategy:
    return FactorRuleStrategy(
        name=overrides.get("name", "value rule"),
        market=overrides.get("market", "A股"),
        channels=overrides.get("channels", ["email", "telegram"]),
        conditions=overrides.get("conditions", [
            Condition("pe_ttm", "<", 15),
            Condition("roe", ">", 10),
        ]),
        condition_logic=overrides.get("condition_logic", "AND"),
    )


# ── Strategy CRUD ────────────────────────────────────────────────────────────

def test_save_then_get_returns_equal_strategy(sess):
    s = _make_strategy()
    repo.save_strategy(sess, s)
    loaded = repo.get_strategy(sess, s.strategy_id)
    assert loaded is not None
    assert loaded.name == s.name
    assert loaded.market == s.market
    assert loaded.channels == s.channels
    assert loaded.conditions == s.conditions
    assert loaded.condition_logic == s.condition_logic


def test_get_missing_strategy_returns_none(sess):
    assert repo.get_strategy(sess, "00000000-0000-0000-0000-000000000000") is None


def test_save_is_idempotent_on_same_id(sess):
    s = _make_strategy()
    repo.save_strategy(sess, s)
    s.name = "renamed"
    repo.save_strategy(sess, s)

    rows = sess.query(models.StrategyRow).filter_by(strategy_id=s.strategy_id).all()
    assert len(rows) == 1
    assert rows[0].name == "renamed"


def test_list_active_excludes_inactive(sess):
    a = _make_strategy(name="active")
    b = _make_strategy(name="inactive")
    b.is_active = False
    repo.save_strategy(sess, a)
    repo.save_strategy(sess, b)

    active = repo.list_active_strategies(sess)
    assert {s.name for s in active} == {"active"}


def test_delete_strategy(sess):
    s = _make_strategy()
    repo.save_strategy(sess, s)
    assert repo.delete_strategy(sess, s.strategy_id) is True
    assert repo.get_strategy(sess, s.strategy_id) is None
    assert repo.delete_strategy(sess, s.strategy_id) is False


# ── Event persistence ────────────────────────────────────────────────────────

def test_save_event_persists_snapshot(sess):
    s = _make_strategy()
    repo.save_strategy(sess, s)

    triggered = Triggered(
        symbol="SH600000",
        name="浦发银行",
        snapshot={"pe_ttm": 4.5, "roe": 12.3},
        event_type="match",
    )
    repo.save_event(sess, s.strategy_id, triggered, asof=date(2026, 5, 5), notified=True)

    events = repo.list_events(sess, strategy_id=s.strategy_id)
    assert len(events) == 1
    e = events[0]
    assert e.symbol == "SH600000"
    assert e.event_type == "match"
    assert e.notified is True
    assert e.notified_at is not None


def test_list_events_orders_by_recent_first_and_filters(sess):
    a = _make_strategy(name="A")
    b = _make_strategy(name="B")
    repo.save_strategy(sess, a)
    repo.save_strategy(sess, b)

    repo.save_event(sess, a.strategy_id,
                    Triggered("SH600000", "x", {}), asof=date(2026, 5, 1))
    repo.save_event(sess, b.strategy_id,
                    Triggered("SZ000001", "y", {}), asof=date(2026, 5, 2))

    only_a = repo.list_events(sess, strategy_id=a.strategy_id)
    assert len(only_a) == 1
    assert only_a[0].symbol == "SH600000"

    all_events = repo.list_events(sess)
    assert len(all_events) == 2


# ── SignalState ──────────────────────────────────────────────────────────────

def test_signal_state_round_trip(sess):
    sid = "test-signal"
    assert repo.get_signal_state(sess, sid) is None

    repo.set_signal_state(sess, sid, date(2026, 5, 5), ["SH600000", "SH600519"])
    state = repo.get_signal_state(sess, sid)
    assert state is not None
    asof, symbols = state
    assert asof == date(2026, 5, 5)
    assert symbols == ["SH600000", "SH600519"]


def test_signal_state_overwrites_on_repeat(sess):
    sid = "test-signal"
    repo.set_signal_state(sess, sid, date(2026, 5, 5), ["SH600000"])
    repo.set_signal_state(sess, sid, date(2026, 5, 6), ["SZ000001", "SH600519"])

    asof, symbols = repo.get_signal_state(sess, sid)
    assert asof == date(2026, 5, 6)
    assert symbols == ["SZ000001", "SH600519"]
