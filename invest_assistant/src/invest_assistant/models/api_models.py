"""API models for request/response."""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel


class StockQuery(BaseModel):
    """Query stock data."""
    symbol: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class StockResponse(BaseModel):
    """Stock data response."""
    symbol: str
    name: str
    exchange: str
    data: dict


class MonitorRuleCreate(BaseModel):
    """Create monitor rule."""
    name: str
    description: Optional[str] = None
    conditions: List[dict]
    condition_logic: str = "AND"
    market: str = "A股"


class MonitorRuleResponse(BaseModel):
    """Monitor rule response."""
    rule_id: str
    name: str
    conditions: List[dict]
    is_active: bool


class MonitorCheckRequest(BaseModel):
    """Manually trigger monitor check."""
    rule_id: Optional[str] = None  # None means check all rules


class MonitorCheckResponse(BaseModel):
    """Monitor check result."""
    rule_id: str
    rule_name: str
    triggered_count: int
    triggered_stocks: List[dict]