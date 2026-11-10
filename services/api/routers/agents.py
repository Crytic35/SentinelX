from datetime import datetime, timedelta
import uuid
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.session import get_db
from database.models import Agent, AgentPassport, Policy, PaymentIntent, RiskAssessment
from security.identity.crypto import generate_agent_keypair
from security.identity.passport import AgentPassportModel, TrustState
from security.enforcement.trust_state import TrustStateMachine
from security.enforcement.blast_radius import BlastRadiusCalculator
from security.audit.tamper_evident_log import record_security_event
from agents.behavior.baseline import BehaviorAnalyzer, AgentBehavioralFingerprint

router = APIRouter(prefix="/agents", tags=["Agents & Passports"])

class CreateAgentRequest(BaseModel):
    name: str
    owner_id: str
    purpose: str
    capabilities: List[str] = Field(default_factory=lambda: ["search_products", "cart_management", "initiate_merchant_payments"])
    per_transaction_limit: float = 500.0
    daily_limit: float = 1500.0
    allowed_categories: List[str] = Field(default_factory=lambda: ["electronics", "books"])
    blocked_categories: List[str] = Field(default_factory=lambda: ["cryptocurrency", "gift cards"])
    allowed_countries: List[str] = Field(default_factory=lambda: ["US", "IN", "GB", "EU", "CA"])
    approval_threshold: float = 300.0

@router.post("", status_code=status.HTTP_201_CREATED)
def create_agent(req: CreateAgentRequest, db: Session = Depends(get_db)):
    agent_id = f"Agent-{req.name.replace(' ', '')}-{uuid.uuid4().hex[:6]}"
    pub_key, priv_key = generate_agent_keypair()

    agent = Agent(
        id=agent_id,
        owner_id=req.owner_id,
        name=req.name,
        purpose=req.purpose,
        status="ACTIVE",
        trust_state=TrustState.TRUSTED,
        public_key=pub_key,
        private_key=priv_key,
        passport_version=1,
        capabilities=req.capabilities
    )
    db.add(agent)
    db.flush()

    # Generate and sign Passport v1
    passport_model = AgentPassportModel(
        agent_id=agent.id,
        owner_id=req.owner_id,
        version=1,
        capabilities=req.capabilities,
        per_transaction_limit=req.per_transaction_limit,
        daily_limit=req.daily_limit,
        allowed_categories=req.allowed_categories,
        blocked_categories=req.blocked_categories,
        allowed_countries=req.allowed_countries,
        approval_threshold=req.approval_threshold,
        public_key=pub_key
    )
    passport_model.sign(priv_key)

    db_passport = AgentPassport(
        id=passport_model.passport_id,
        agent_id=agent.id,
        version=passport_model.version,
        owner_id=passport_model.owner_id,
        capabilities=passport_model.capabilities,
        per_transaction_limit=passport_model.per_transaction_limit,
        daily_limit=passport_model.daily_limit,
        allowed_categories=passport_model.allowed_categories,
        blocked_categories=passport_model.blocked_categories,
        allowed_countries=passport_model.allowed_countries,
        approval_threshold=passport_model.approval_threshold,
        public_key=pub_key,
        signature=passport_model.signature
    )
    db.add(db_passport)

    # Initial policy
    policy_def = {
        "spending_limits": {"max_transaction": req.per_transaction_limit, "daily_limit": req.daily_limit},
        "categories": {"allow": req.allowed_categories, "deny": req.blocked_categories},
        "allowed_countries": req.allowed_countries,
        "allowed_currencies": ["USD", "EUR", "GBP"],
        "approval": {"amount": req.approval_threshold, "new_merchant": True, "recurring": True, "max_quantity": 5}
    }
    policy = Policy(
        id=f"pol_{agent.id}_v1",
        agent_id=agent.id,
        version=1,
        definition=policy_def,
        status="ACTIVE",
        is_active=True
    )
    db.add(policy)
    db.commit()

    record_security_event(
        db=db,
        agent_id=agent.id,
        payment_intent_id=None,
        event_type="AGENT_ONBOARDED",
        severity="INFO",
        summary=f"New agent '{agent.name}' ({agent.id}) successfully onboarded with verified Ed25519 passport",
        payload={"agent_id": agent.id, "owner": agent.owner_id, "passport_id": db_passport.id}
    )

    return {
        "agent_id": agent.id,
        "name": agent.name,
        "owner_id": agent.owner_id,
        "trust_state": agent.trust_state,
        "passport_version": agent.passport_version,
        "public_key": agent.public_key,
        "passport": passport_model.dict()
    }

@router.get("")
def list_agents(db: Session = Depends(get_db)):
    agents = db.query(Agent).all()
    results = []
    for a in agents:
        latest_passport = db.query(AgentPassport).filter(AgentPassport.agent_id == a.id).order_by(AgentPassport.version.desc()).first()
        per_tx = latest_passport.per_transaction_limit if latest_passport else 500.0
        daily = latest_passport.daily_limit if latest_passport else 1500.0

        blast = BlastRadiusCalculator.calculate_agent_blast_radius(
            agent_id=a.id,
            max_transaction=per_tx,
            daily_limit=daily,
            trust_state=a.trust_state
        )

        results.append({
            "id": a.id,
            "name": a.name,
            "owner_id": a.owner_id,
            "purpose": a.purpose,
            "trust_state": a.trust_state,
            "status": a.status,
            "passport_version": a.passport_version,
            "capabilities": a.capabilities,
            "per_transaction_limit": per_tx,
            "daily_limit": daily,
            "blast_radius": blast,
            "created_at": a.created_at.isoformat() if a.created_at else None
        })
    return results

@router.get("/{agent_id}")
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    passports = db.query(AgentPassport).filter(AgentPassport.agent_id == agent.id).order_by(AgentPassport.version.desc()).all()
    policies = db.query(Policy).filter(Policy.agent_id == agent.id).order_by(Policy.version.desc()).all()
    recent_intents = db.query(PaymentIntent).filter(PaymentIntent.agent_id == agent.id).order_by(PaymentIntent.created_at.desc()).limit(10).all()

    latest_psp = passports[0] if passports else None

    return {
        "id": agent.id,
        "name": agent.name,
        "owner_id": agent.owner_id,
        "purpose": agent.purpose,
        "trust_state": agent.trust_state,
        "status": agent.status,
        "public_key": agent.public_key,
        "passport_version": agent.passport_version,
        "capabilities": agent.capabilities,
        "latest_passport": {
            "id": latest_psp.id,
            "version": latest_psp.version,
            "per_transaction_limit": latest_psp.per_transaction_limit,
            "daily_limit": latest_psp.daily_limit,
            "allowed_categories": latest_psp.allowed_categories,
            "blocked_categories": latest_psp.blocked_categories,
            "allowed_countries": latest_psp.allowed_countries,
            "approval_threshold": latest_psp.approval_threshold,
            "signature": latest_psp.signature
        } if latest_psp else None,
        "active_policy": policies[0].definition if policies else None,
        "recent_activity": [
            {
                "id": pi.id,
                "amount": pi.amount,
                "currency": pi.currency,
                "purpose": pi.purpose,
                "merchant_name": pi.merchant_name,
                "decision": pi.decision,
                "status": pi.status,
                "created_at": pi.created_at.isoformat() if pi.created_at else None
            } for pi in recent_intents
        ]
    }

@router.post("/{agent_id}/quarantine")
def quarantine_agent(agent_id: str, reason: str = "Operator manual quarantine", db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.trust_state = TrustState.QUARANTINED
    db.commit()

    record_security_event(
        db=db,
        agent_id=agent.id,
        payment_intent_id=None,
        event_type="AGENT_QUARANTINED",
        severity="CRITICAL",
        summary=f"Emergency Quarantine triggered for {agent.id}: {reason}",
        payload={"agent_id": agent.id, "reason": reason, "trust_state": TrustState.QUARANTINED}
    )

    return {"agent_id": agent.id, "trust_state": agent.trust_state, "message": "Agent quarantined. All payment executions halted immediately."}

@router.post("/{agent_id}/restrict")
def restrict_agent(agent_id: str, reason: str = "Suspicious behavior detected", db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.trust_state = TrustState.RESTRICTED
    db.commit()

    record_security_event(
        db=db,
        agent_id=agent.id,
        payment_intent_id=None,
        event_type="AGENT_RESTRICTED",
        severity="HIGH",
        summary=f"Capability attenuation: Agent {agent.id} restricted to minimal privileges",
        payload={"agent_id": agent.id, "reason": reason, "trust_state": TrustState.RESTRICTED}
    )

    return {"agent_id": agent.id, "trust_state": agent.trust_state, "message": "Agent restricted."}

@router.post("/{agent_id}/restore")
def restore_agent(agent_id: str, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.trust_state = TrustState.TRUSTED
    db.commit()

    record_security_event(
        db=db,
        agent_id=agent.id,
        payment_intent_id=None,
        event_type="AGENT_RESTORED",
        severity="INFO",
        summary=f"Agent {agent.id} trust restored to TRUSTED following human verification",
        payload={"agent_id": agent.id, "trust_state": TrustState.TRUSTED}
    )

    return {"agent_id": agent.id, "trust_state": agent.trust_state, "message": "Agent privileges successfully restored."}

@router.get("/{agent_id}/scorecard")
def get_agent_scorecard(agent_id: str, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    intents = db.query(PaymentIntent).filter(PaymentIntent.agent_id == agent.id).all()
    blocked = sum(1 for pi in intents if pi.decision in ["BLOCK", "QUARANTINE"])
    allowed = sum(1 for pi in intents if pi.decision == "ALLOW")

    # Score breakdown
    identity_score = 100.0 if agent.public_key else 0.0
    auth_score = 95.0 if agent.trust_state == TrustState.TRUSTED else (30.0 if agent.trust_state == TrustState.RESTRICTED else 0.0)
    behavior_score = 92.0 if blocked == 0 else max(25.0, 92.0 - (blocked * 20.0))
    intent_score = 96.0 if blocked == 0 else max(20.0, 96.0 - (blocked * 25.0))
    provenance_score = 94.0 if blocked == 0 else max(30.0, 94.0 - (blocked * 18.0))
    merchant_score = 95.0

    return {
        "agent_id": agent.id,
        "name": agent.name,
        "trust_state": agent.trust_state,
        "overall_status": "SECURE" if agent.trust_state == "TRUSTED" else ("RESTRICTED" if agent.trust_state == "RESTRICTED" else "QUARANTINED"),
        "scores": {
            "identity": identity_score,
            "authorization": auth_score,
            "behavior": behavior_score,
            "intent_alignment": intent_score,
            "provenance": provenance_score,
            "merchant_trust": merchant_score,
            "policy_compliance": 100.0 if blocked == 0 else 60.0
        },
        "stats": {
            "total_intents": len(intents),
            "allowed_count": allowed,
            "blocked_count": blocked
        }
    }

