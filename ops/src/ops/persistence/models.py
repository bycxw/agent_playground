"""SQLAlchemy ORM models for ops state.

Three tables:
  - strategies   : polymorphic strategy storage (type + config_json)
  - events       : trigger history (match / enter_topk / exit_topk)
  - signal_state : last-evaluated Top-K snapshots, for signal-strategy diffs
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class StrategyRow(Base):
    """Persistent strategy. Concrete type lives in `type` + `config_json`."""
    __tablename__ = "strategies"

    strategy_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name:        Mapped[str] = mapped_column(String(255))
    type:        Mapped[str] = mapped_column(String(64), index=True)
    config_json: Mapped[str] = mapped_column(Text)
    market:      Mapped[str] = mapped_column(String(16), default="A股")
    channels:    Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    is_active:   Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at:  Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at:  Mapped[datetime] = mapped_column(DateTime, default=datetime.now,
                                                   onupdate=datetime.now)

    events: Mapped[list["EventRow"]] = relationship(back_populates="strategy")


class EventRow(Base):
    """One Triggered persisted. snapshot_json carries the strategy-specific payload."""
    __tablename__ = "events"

    event_id:      Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id:   Mapped[str] = mapped_column(String(36), ForeignKey("strategies.strategy_id"),
                                                index=True)
    symbol:        Mapped[str] = mapped_column(String(16), index=True)  # canonical
    asof:          Mapped[date] = mapped_column(Date, index=True)
    event_type:    Mapped[str] = mapped_column(String(32))  # match / enter_topk / exit_topk
    snapshot_json: Mapped[str] = mapped_column(Text)
    notified:      Mapped[bool] = mapped_column(Boolean, default=False)
    notified_at:   Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    triggered_at:  Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    strategy: Mapped[StrategyRow] = relationship(back_populates="events")


class SignalStateRow(Base):
    """Last-evaluated Top-K membership for a signal strategy.

    Used by SignalTopKStrategy to detect enter/exit transitions without
    re-reading historical parquet on every check.
    """
    __tablename__ = "signal_state"

    strategy_id:   Mapped[str] = mapped_column(String(36), primary_key=True)
    asof:          Mapped[date] = mapped_column(Date)
    snapshot_json: Mapped[str] = mapped_column(Text)  # JSON list of canonical symbols
    updated_at:    Mapped[datetime] = mapped_column(DateTime, default=datetime.now,
                                                     onupdate=datetime.now)
