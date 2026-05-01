"""Simple test for import validation."""
from invest_assistant.models import MonitorRule, MonitorEvent
from invest_assistant.core.monitor import MonitorEngine, ConditionEvaluator

def test_monitor_rule():
    """Test monitor rule creation."""
    rule = MonitorRule(
        name="Test Rule",
        conditions=[{"field": "pe_ttm", "op": "<", "value": 15}],
    )
    assert rule.name == "Test Rule"
    assert len(rule.conditions) == 1
    print("✅ MonitorRule created successfully")


def test_condition_evaluator():
    """Test condition evaluator."""
    import pandas as pd

    row = pd.Series({
        "pe_ttm": 12.5,
        "roe": 15.0,
    })

    # Test less than
    cond = {"field": "pe_ttm", "op": "<", "value": 15}
    assert ConditionEvaluator.evaluate(row, cond) == True

    # Test greater than
    cond = {"field": "roe", "op": ">", "value": 10}
    assert ConditionEvaluator.evaluate(row, cond) == True

    # Test failed condition
    cond = {"field": "pe_ttm", "op": ">", "value": 20}
    assert ConditionEvaluator.evaluate(row, cond) == False

    print("✅ ConditionEvaluator works correctly")


if __name__ == "__main__":
    test_monitor_rule()
    test_condition_evaluator()
    print("\n✅ All basic tests passed!")