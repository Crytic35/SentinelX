import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.session import get_db
from database.models import Agent, Policy, PaymentIntent
from security.policies.schema import PolicyDefinition, SpendingLimits, CategoryPolicy, ApprovalRules
from security.policies.engine import PolicyEngine
from security.policies.natural_language import parse_natural_language_policy
from security.audit.tamper_evident_log import record_security_event

router = APIRouter(prefix="/policies", tags=["Policies & Policy-as-Code"])

class NaturalLanguagePolicyRequest(BaseModel):
    agent_id: str = "ShoppingAgent-42"
    prompt: str

class PolicySimulationRequest(BaseModel):
    agent_id: str
    proposed_policy: Dict[str, Any]

@router.get("/{agent_id}")
def get_agent_policies(agent_id: str, db: Session = Depends(get_db)):
    policies = db.query(Policy).filter(Policy.agent_id == agent_id).order_by(Policy.version.desc()).all()
    if not policies:
        raise HTTPException(status_code=404, detail="No policies found for agent")
    return [
        {
            "id": p.id,
            "version": p.version,
            "definition": p.definition,
            "status": p.status,
            "is_active": p.is_active,
            "created_at": p.created_at.isoformat() if p.created_at else None
        } for p in policies
    ]

@router.post("/natural-language")
def convert_natural_language_to_policy(req: NaturalLanguagePolicyRequest):
    policy, error = parse_natural_language_policy(req.prompt, agent_id=req.agent_id)
    if error:
        raise HTTPException(status_code=422, detail=error)
    return {
        "status": "VALID",
        "proposed_policy": policy.dict(),
        "prompt": req.prompt,
        "conflict_checks_passed": True
    }

@router.post("/{agent_id}")
def update_agent_policy(agent_id: str, definition: Dict[str, Any], db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Validate against schema
    try:
        policy_def = PolicyDefinition(**definition, agent_id=agent_id)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Policy schema validation failed: {str(e)}")

    # Archive previous active policies
    active_policies = db.query(Policy).filter(Policy.agent_id == agent_id, Policy.is_active == True).all()
    latest_version = 1
    for p in active_policies:
        p.is_active = False
        p.status = "SUPERSEDED"
        if p.version >= latest_version:
            latest_version = p.version + 1

    new_policy = Policy(
        id=f"pol_{agent_id}_v{latest_version}",
        agent_id=agent_id,
        version=latest_version,
        definition=policy_def.dict(),
        status="ACTIVE",
        is_active=True
    )
    db.add(new_policy)
    db.commit()

    record_security_event(
        db=db,
        agent_id=agent_id,
        payment_intent_id=None,
        event_type="POLICY_UPDATED",
        severity="INFO",
        summary=f"Policy updated to v{latest_version} for agent {agent_id}",
        payload={"agent_id": agent_id, "new_version": latest_version, "definition": policy_def.dict()}
    )

    return {"status": "SUCCESS", "version": latest_version, "policy_id": new_policy.id}

@router.post("/simulate")
def simulate_policy_against_history(req: PolicySimulationRequest, db: Session = Depends(get_db)):
    try:
        proposed = PolicyDefinition(**req.proposed_policy, agent_id=req.agent_id)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid proposed policy schema: {str(e)}")

    # Replay against historical payment intents
    intents = db.query(PaymentIntent).filter(PaymentIntent.agent_id == req.agent_id).all()
    if not intents:
        return {
            "historical_transactions_analyzed": 0,
            "allowed_count": 0,
            "blocked_count": 0,
            "step_up_count": 0,
            "impact_summary": "No historical transactions found for replay comparison."
        }

    results = []
    newly_blocked = 0
    newly_step_up = 0
    legitimate_impacted = 0

    for pi in intents:
        check = PolicyEngine.evaluate(
            policy=proposed,
            amount=pi.amount,
            currency=pi.currency,
            category=pi.category,
            merchant_id=pi.merchant_id,
            merchant_country="US",
            is_new_merchant=False,
            quantity=pi.quantity,
            is_recurring=pi.is_recurring,
            current_daily_spend=0.0
        )
        was_allowed = pi.decision == "ALLOW"
        now_allowed = check.allowed and not check.requires_step_up

        if was_allowed and not check.allowed:
            newly_blocked += 1
            legitimate_impacted += 1
        elif was_allowed and check.requires_step_up:
            newly_step_up += 1

        results.append({
            "intent_id": pi.id,
            "amount": pi.amount,
            "category": pi.category,
            "previous_decision": pi.decision,
            "proposed_decision": check.decision,
            "violations": check.violations
        })

    return {
        "historical_transactions_analyzed": len(intents),
        "newly_blocked_count": newly_blocked,
        "newly_requiring_approval_count": newly_step_up,
        "legitimate_transactions_impacted": legitimate_impacted,
        "over_restriction_warning": legitimate_impacted > 0,
        "sample_evaluations": results[:10]
    }

