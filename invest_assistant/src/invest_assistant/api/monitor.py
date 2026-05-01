"""API routes - monitor endpoints."""
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..models import MonitorRuleCreate, MonitorRuleResponse, MonitorCheckResponse
from ..core.monitor import get_engine, add_rule, remove_rule, check_all
from ..models import MonitorRule

router = APIRouter(prefix="/monitor", tags=["monitor"])


class AddRuleRequest(BaseModel):
    """Add monitor rule request."""
    name: str
    description: Optional[str] = None
    conditions: List[dict]
    condition_logic: str = "AND"
    market: str = "A股"


class AddRuleResponse(BaseModel):
    """Add rule response."""
    rule_id: str
    message: str


class RemoveRuleRequest(BaseModel):
    """Remove rule request."""
    rule_id: str


class CheckRuleRequest(BaseModel):
    """Check specific rule request."""
    rule_id: Optional[str] = None


@router.get("/rules", response_model=List[MonitorRuleResponse])
async def get_rules():
    """Get all monitor rules."""
    engine = get_engine()
    rules = engine.get_rules()

    return [
        MonitorRuleResponse(
            rule_id=str(r.rule_id),
            name=r.name,
            conditions=r.conditions,
            is_active=r.is_active,
        )
        for r in rules
    ]


@router.post("/rules", response_model=AddRuleResponse)
async def create_rule(request: AddRuleRequest):
    """Create a new monitor rule."""
    rule = MonitorRule(
        name=request.name,
        description=request.description,
        conditions=request.conditions,
        condition_logic=request.condition_logic,
        market=request.market,
    )

    add_rule(rule)

    return AddRuleResponse(
        rule_id=str(rule.rule_id),
        message=f"Rule '{request.name}' created successfully",
    )


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str):
    """Delete a monitor rule."""
    engine = get_engine()
    existing = [r for r in engine.get_rules() if str(r.rule_id) == rule_id]

    if not existing:
        raise HTTPException(status_code=404, detail="Rule not found")

    remove_rule(rule_id)

    return {"message": f"Rule {rule_id} deleted"}


@router.post("/check", response_model=List[MonitorCheckResponse])
async def check_rules(rule_id: Optional[str] = None):
    """Trigger monitor check for all rules or specific rule."""
    engine = get_engine()

    if rule_id:
        # Check specific rule
        rules = [r for r in engine.get_rules() if str(r.rule_id) == rule_id]
        if not rules:
            raise HTTPException(status_code=404, detail="Rule not found")

        results = {}
        for rule in rules:
            triggered = engine.check_rule(rule)
            results[str(rule.rule_id)] = triggered

    else:
        # Check all rules
        results = check_all()

    # Format response
    response = []
    engine = get_engine()
    for rid, triggered in results.items():
        rule = next((r for r in engine.get_rules() if str(r.rule_id) == rid), None)
        response.append(
            MonitorCheckResponse(
                rule_id=rid,
                rule_name=rule.name if rule else rid,
                triggered_count=len(triggered),
                triggered_stocks=triggered[:20],  # Limit to 20 in response
            )
        )

    return response


@router.get("/events")
async def get_events(rule_id: Optional[str] = None, limit: int = 100):
    """Get monitor events."""
    engine = get_engine()
    events = engine.get_events(rule_id=rule_id, limit=limit)

    return [
        {
            "event_id": str(e.event_id),
            "rule_id": str(e.rule_id),
            "symbol": e.symbol,
            "trigger_time": e.trigger_time.isoformat(),
            "trigger_data": e.trigger_data,
            "notified": e.notified,
        }
        for e in events
    ]