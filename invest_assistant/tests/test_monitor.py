"""Tests for strategies, persistence, channel dispatch."""
import pandas as pd
import pytest

from invest_assistant.notification.channel import (
    NotificationChannel,
    dispatch,
    register_channel,
)
from invest_assistant.strategies import (
    Condition,
    FactorRuleStrategy,
    Triggered,
    known_types,
    lookup,
)
from invest_assistant.strategies.factor_rule import _evaluate_condition


# ── Conditions ───────────────────────────────────────────────────────────────

def test_condition_evaluator_basic():
    row = pd.Series({"pe_ttm": 12.5, "roe": 15.0})
    assert _evaluate_condition(row, Condition("pe_ttm", "<", 15)) is True
    assert _evaluate_condition(row, Condition("roe", ">", 10)) is True
    assert _evaluate_condition(row, Condition("pe_ttm", ">", 20)) is False


def test_condition_evaluator_handles_missing_field():
    row = pd.Series({"pe_ttm": 12.5})
    assert _evaluate_condition(row, Condition("nonexistent", "<", 1)) is False


def test_condition_evaluator_handles_nan():
    row = pd.Series({"pe_ttm": float("nan")})
    assert _evaluate_condition(row, Condition("pe_ttm", "<", 15)) is False


# ── Strategy registry / serde ────────────────────────────────────────────────

def test_factor_rule_registered():
    assert "factor_rule" in known_types()
    assert lookup("factor_rule") is FactorRuleStrategy


def test_factor_rule_round_trip():
    s = FactorRuleStrategy(
        name="value rule",
        market="A股",
        channels=["email"],
        conditions=[Condition("pe_ttm", "<", 15), Condition("roe", ">", 10)],
        condition_logic="AND",
    )
    cfg = s.to_config()
    rebuilt = FactorRuleStrategy.from_config(
        cfg,
        name=s.name,
        market=s.market,
        channels=s.channels,
        strategy_id=s.strategy_id,
    )
    assert rebuilt.conditions == s.conditions
    assert rebuilt.condition_logic == s.condition_logic
    assert rebuilt.name == s.name


# ── Channel dispatch ─────────────────────────────────────────────────────────

class _RecordingChannel(NotificationChannel):
    def __init__(self):
        self.calls: list[tuple[str, list[Triggered]]] = []

    def send(self, strategy_name, triggered):
        self.calls.append((strategy_name, triggered))


def test_dispatch_routes_to_registered_channels():
    rec = _RecordingChannel()
    register_channel("__test_recording__", rec)

    triggered = [Triggered(symbol="SH600000", name="X", snapshot={"pe": 5})]
    dispatch("my strategy", triggered, ["__test_recording__"])

    assert rec.calls == [("my strategy", triggered)]


def test_dispatch_skips_unregistered_channel(caplog):
    triggered = [Triggered(symbol="SH600000", name="X", snapshot={})]
    # Should warn but not raise
    dispatch("s", triggered, ["__nonexistent__"])


def test_dispatch_swallows_channel_failure():
    class _Failing(NotificationChannel):
        def send(self, *_):
            raise RuntimeError("boom")

    register_channel("__failing__", _Failing())
    # Should log + continue, not propagate
    dispatch("s", [Triggered(symbol="SH600000", name="X", snapshot={})], ["__failing__"])
