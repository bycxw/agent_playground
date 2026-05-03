"""Monitor engine - core logic for monitoring stocks."""
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import pandas as pd

from ...providers import query_all_financial_metrics, query_stock_list
from ...models import MonitorRule, MonitorEvent
from ..notification import NotificationSender

logger = logging.getLogger(__name__)


class ConditionEvaluator:
    """Evaluate single condition against a data row."""

    OPERATORS = {
        "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b,
        ">": lambda a, b: a > b,
        ">=": lambda a, b: a >= b,
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
    }

    @classmethod
    def evaluate(cls, row: pd.Series, condition: dict) -> bool:
        """Evaluate single condition.

        Args:
            row: Data row with field values
            condition: {"field": "pe_ttm", "op": "<", "value": 15}

        Returns:
            True if condition is met
        """
        field = condition.get("field")
        op = condition.get("op")
        value = condition.get("value")

        if field not in row.index:
            logger.warning(f"Field {field} not in data row")
            return False

        field_value = row[field]

        # Handle None/NaN
        if pd.isna(field_value):
            return False

        op_func = cls.OPERATORS.get(op)
        if not op_func:
            logger.warning(f"Unknown operator: {op}")
            return False

        try:
            return op_func(float(field_value), float(value))
        except (ValueError, TypeError):
            return False


class MonitorEngine:
    """Main monitor engine."""

    def __init__(self):
        self.rules: List[MonitorRule] = []
        self.events: List[MonitorEvent] = []
        self.notifier = NotificationSender()

    def add_rule(self, rule: MonitorRule) -> None:
        """Add a monitor rule."""
        self.rules.append(rule)
        logger.info(f"Added rule: {rule.name} ({rule.rule_id})")

    def remove_rule(self, rule_id: str) -> None:
        """Remove a monitor rule by ID."""
        self.rules = [r for r in self.rules if str(r.rule_id) != rule_id]
        logger.info(f"Removed rule: {rule_id}")

    def get_rules(self) -> List[MonitorRule]:
        """Get all rules."""
        return self.rules

    def check_rule(self, rule: MonitorRule, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Check a single rule against pre-fetched stock data.

        Args:
            rule: Monitor rule to evaluate
            df: Pre-fetched financial metrics DataFrame for the market

        Returns:
            List of stocks that triggered the rule
        """
        logger.info(f"Checking rule: {rule.name}")

        if df.empty:
            logger.warning(f"Empty dataframe for rule: {rule.name}")
            return []

        # Evaluate conditions
        triggered = []

        for _, row in df.iterrows():
            # All conditions must match (AND) or any match (OR)
            if rule.condition_logic == "AND":
                matches = all(
                    ConditionEvaluator.evaluate(row, cond)
                    for cond in rule.conditions
                )
            else:
                matches = any(
                    ConditionEvaluator.evaluate(row, cond)
                    for cond in rule.conditions
                )

            if matches:
                stock_info = {
                    "symbol": row.get("symbol", ""),
                    "name": row.get("name", ""),
                    "entity_id": row.get("entity_id", ""),
                }

                # Add all condition fields to snapshot
                snapshot = {cond["field"]: row.get(cond["field"]) for cond in rule.conditions}
                stock_info["snapshot"] = snapshot

                triggered.append(stock_info)

        logger.info(f"Rule {rule.name}: {len(triggered)} stocks triggered")
        return triggered

    def check_all_rules(self) -> Dict[str, List[Dict]]:
        """Check all active rules.

        Fetches market data once per market to avoid redundant queries.

        Returns:
            Dict mapping rule_id to triggered stocks
        """
        active_rules = [r for r in self.rules if r.is_active]
        if not active_rules:
            return {}

        # Group rules by market to fetch data only once per market
        rules_by_market: Dict[str, List[MonitorRule]] = {}
        for rule in active_rules:
            rules_by_market.setdefault(rule.market, []).append(rule)

        # Fetch data once per market
        market_data: Dict[str, pd.DataFrame] = {}
        for market in rules_by_market:
            try:
                market_data[market] = query_all_financial_metrics(market=market)
                logger.info(f"Fetched data for market '{market}': {len(market_data[market])} stocks")
            except Exception as e:
                logger.error(f"Failed to fetch data for market '{market}': {e}")
                market_data[market] = pd.DataFrame()

        # Evaluate each rule against its market data
        results = {}
        for market, rules in rules_by_market.items():
            df = market_data[market]
            for rule in rules:
                triggered = self.check_rule(rule, df)

                if triggered:
                    # Record events
                    for stock in triggered:
                        event = MonitorEvent(
                            rule_id=rule.rule_id,
                            symbol=stock["symbol"],
                            trigger_data=stock["snapshot"],
                        )
                        self.events.append(event)

                    # Send notifications
                    self.notifier.send(
                        rule_name=rule.name,
                        stocks=triggered,
                        conditions=rule.conditions,
                    )

                    results[str(rule.rule_id)] = triggered

        return results

    def get_events(
        self,
        rule_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[MonitorEvent]:
        """Get monitor events."""
        events = self.events

        if rule_id:
            events = [e for e in events if str(e.rule_id) == rule_id]

        return events[-limit:]


# Global engine instance
_engine: Optional[MonitorEngine] = None


def get_engine() -> MonitorEngine:
    """Get global monitor engine instance."""
    global _engine
    if _engine is None:
        _engine = MonitorEngine()
    return _engine


def add_rule(rule: MonitorRule) -> None:
    """Add rule to global engine."""
    get_engine().add_rule(rule)


def remove_rule(rule_id: str) -> None:
    """Remove rule from global engine."""
    get_engine().remove_rule(rule_id)


def check_all() -> Dict[str, List[Dict]]:
    """Check all rules."""
    return get_engine().check_all_rules()