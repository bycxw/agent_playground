"""Database schemas for Invest Assistant business models."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class MonitorRule(BaseModel):
    """Monitor rule definition."""

    rule_id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None

    # Conditions: [{"field": "pe_ttm", "op": "<", "value": 15}]
    conditions: List[dict]

    # AND/OR logic for multiple conditions
    condition_logic: str = "AND"

    # Market scope
    market: str = "A股"  # A股/港股/ALL

    # Status
    is_active: bool = True

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class MonitorEvent(BaseModel):
    """Monitor trigger event."""

    event_id: UUID = Field(default_factory=uuid4)
    rule_id: UUID
    symbol: str
    trigger_time: datetime = Field(default_factory=datetime.now)

    # Snapshot of data when triggered
    trigger_data: dict

    # Notification status
    notified: bool = False
    notified_at: Optional[datetime] = None

    # Notes
    memo: Optional[str] = None


class MonitorStockPool(BaseModel):
    """Stock pool for monitoring."""

    id: int = Field(default_factory=lambda: 0)
    rule_id: UUID
    symbol: str  # e.g., "000001.SZ"
    added_at: datetime = Field(default_factory=datetime.now)