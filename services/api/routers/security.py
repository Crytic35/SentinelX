from datetime import datetime, timedelta
import uuid
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.session import get_db
from database.models import Agent, AgentPassport, Policy, PaymentIntent, RiskAssessment, SecurityEvent, Payment
from security.identity.passport import TrustState
from security.identity.crypto import verify_signature
from security.policies.schema import PolicyDefinition, SpendingLimits, CategoryPolicy, ApprovalRules
from security.policies.engine import PolicyEngine
from security.replay.nonce_store import nonce_store
from security.provenance.tracker import ProvenanceTracker
from security.provenance.graph import build_provenance_graph
from security.merchant.registry import MerchantSecurityService
from agents.intent.analyzer import IntentAnalyzer, StructuredIntent
from agents.intent.drift_detector import IntentDriftDetector
from agents.behavior.baseline import BehaviorAnalyzer, AgentBehavioralFingerprint
from agents.risk.risk_engine import RiskEngine
from agents.risk.explainable import ExplainableRiskService
from security.audit.tamper_evident_log import record_security_event, verify_audit_chain
from services.api.config import settings

router = APIRouter(prefix="/security", tags=["Security Gateway & Authorization"])

class PaymentEvaluationRequest(BaseModel):
    agent_id: str
    user_goal: str
    purpose: str
    amount: float
    currency: str = "USD"
    category: str
    quantity: int = 1
    merchant_id: str
    merchant_name: str
    merchant_country: str = "US"
    is_recurring: bool = False
    recurring_period: Optional[str] = None
    expected_merchant_id: Optional[str] = None
    nonce: str
    timestamp: str
    signature: Optional[str] = None
    execution_steps: List[Dict[str, Any]] = Field(default_factory=list)
    dry_run: bool = False

class HumanApprovalRequest(BaseModel):
    payment_intent_id: str
    action: str = Field(..., description="APPROVE_ONCE, RESTRICT_AGENT, QUARANTINE, REJECT")
    approved_by: str = "SecOps Lead"
    scope: str = "ONCE"  # ONCE, MERCHANT_WINDOW, LIMIT_SPECIFIC
    notes: Optional[str] = None

@router.post("/evaluate")
def evaluate_payment_request(req: PaymentEvaluationRequest, db: Session = Depends(get_db)):
    # 0. Check Global Freeze
    if settings.GLOBAL_FREEZE:
        raise HTTPException(status_code=503, detail="Global Security Freeze is ACTIVE. All payment authorizations suspended.")

    # 1. Fetch Agent
    agent = db.query(Agent).filter(Agent.id == req.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{req.agent_id}' is not registered with SentinelX")

    # 2. Cryptographic Replay and Nonce Validation
    replay_valid, replay_msg = nonce_store.validate_and_record_nonce(req.nonce, req.timestamp)
    velocity_count = nonce_store.record_agent_request(req.agent_id)

    # 3. Cryptographic Signature Verification (if signature provided)
    if req.signature:
        sig_payload = {
            "agent_id": req.agent_id,
            "user_goal": req.user_goal,
            "amount": float(req.amount),
            "currency": req.currency,
            "category": req.category,
            "quantity": req.quantity,
            "nonce": req.nonce
        }
        # Verify against agent public key
        # If simulated demo agent with zero hex key, accept, else verify
        if agent.public_key and not agent.public_key.startswith("0000"):
            is_sig_valid = verify_signature(sig_payload, req.signature, agent.public_key)
            if not is_sig_valid:
                replay_valid = False
                replay_msg = "Cryptographic signature verification failed: invalid signature for agent public key"

    # 4. Instruction Provenance Tracking
    prov_score = ProvenanceTracker.calculate_provenance_score(req.execution_steps)

    # 5. Intent Analyzer and Drift Detection
    expected_intent = IntentAnalyzer.extract_expected_intent(req.user_goal)
    req_dict = req.dict()
    drift_report = IntentDriftDetector.detect_drift(expected_intent, req_dict, req.execution_steps)

    # 6. Behavioral Fingerprint and Anomaly Analysis
    fingerprint = AgentBehavioralFingerprint(agent_id=req.agent_id)
    behavior_result = BehaviorAnalyzer.evaluate_behavior(
        fingerprint=fingerprint,
        amount=req.amount,
        category=req.category,
        merchant_id=req.merchant_id,
        merchant_country=req.merchant_country
    )

    # 7. Merchant Security and Destination Binding
    is_dest_valid, is_new_merch, merch_trust_score, merch_anomalies = MerchantSecurityService.verify_merchant(
        merchant_id=req.merchant_id,
        merchant_name=req.merchant_name,
        category=req.category,
        expected_merchant_id=req.expected_merchant_id
    )

    # 8. Load Agent Policy
    db_policy = db.query(Policy).filter(Policy.agent_id == req.agent_id, Policy.is_active == True).first()
    if not db_policy:
        # Fallback to standard baseline policy
        policy_def = PolicyDefinition(
            agent_id=req.agent_id,
            version=1,
            spending_limits=SpendingLimits(max_transaction=500.0, daily_limit=1500.0),
            categories=CategoryPolicy(allow=["electronics", "books"], deny=["cryptocurrency", "gift cards"]),
            allowed_countries=["US", "IN", "GB", "EU", "CA"],
            allowed_currencies=["USD", "EUR", "GBP"],
            approval=ApprovalRules(amount=300.0, new_merchant=True, recurring=True, max_quantity=5)
        )
    else:
        policy_def = PolicyDefinition(**db_policy.definition, agent_id=req.agent_id)

    # Calculate current daily spend in last 24h
    one_day_ago = datetime.utcnow() - timedelta(hours=24)
    past_intents = db.query(PaymentIntent).filter(
        PaymentIntent.agent_id == req.agent_id,
        PaymentIntent.status.in_(["ALLOWED", "EXECUTED", "APPROVED"]),
        PaymentIntent.created_at >= one_day_ago
    ).all()
    current_daily_spend = sum(pi.amount for pi in past_intents)

    # 9. Deterministic Policy Engine Evaluation
    policy_result = PolicyEngine.evaluate(
        policy=policy_def,
        amount=req.amount,
        currency=req.currency,
        category=req.category,
        merchant_id=req.merchant_id,
        merchant_country=req.merchant_country,
        is_new_merchant=is_new_merch,
        quantity=req.quantity,
        is_recurring=req.is_recurring,
        current_daily_spend=current_daily_spend
    )

    # 10. Risk Engine Synthesis
    risk_output = RiskEngine.evaluate(
        agent_trust_state=agent.trust_state,
        policy_result=policy_result,
        intent_report=drift_report,
        behavior_result=behavior_result,
        provenance_score=prov_score,
        merchant_trust_score=merch_trust_score,
        merchant_anomalies=merch_anomalies,
        replay_valid=replay_valid,
        replay_message=replay_msg,
        velocity_count_last_minute=velocity_count
    )

    # Human-readable explanation
    risk_output.explanation = ExplainableRiskService.generate_explanation(
        assessment=risk_output,
        agent_id=req.agent_id,
        amount=req.amount,
        merchant_name=req.merchant_name
    )

    # In Shadow Mode, record evaluation but do not block execution
    effective_decision = risk_output.decision
    if settings.SHADOW_MODE and effective_decision in ["BLOCK", "STEP-UP"]:
        effective_decision = "ALLOW_SHADOW_MODE"

    # 11. State Transition
    if not req.dry_run:
        if risk_output.decision == "QUARANTINE" or (risk_output.overall_risk == "CRITICAL" and risk_output.decision == "BLOCK"):
            agent.trust_state = TrustState.QUARANTINED
            db.commit()
        elif risk_output.decision == "RESTRICT":
            agent.trust_state = TrustState.RESTRICTED
            db.commit()

    # 12. Create PaymentIntent Record
    intent_id = f"pi_{uuid.uuid4().hex[:12]}"
    if not req.dry_run:
        intent = PaymentIntent(
            id=intent_id,
            agent_id=req.agent_id,
            user_goal=req.user_goal,
            purpose=req.purpose,
            merchant_id=req.merchant_id,
            merchant_name=req.merchant_name,
            amount=req.amount,
            currency=req.currency,
            category=req.category,
            quantity=req.quantity,
            is_recurring=req.is_recurring,
            recurring_period=req.recurring_period,
            instruction_source="USER",
            signed_payload=req.dict(),
            nonce=req.nonce,
            signature=req.signature or "unsigned_sandbox_dev",
            status="PENDING_APPROVAL" if risk_output.decision == "STEP-UP" else ("ALLOWED" if risk_output.decision == "ALLOW" else "BLOCKED"),
            decision=risk_output.decision,
            approval_status="PENDING" if risk_output.decision == "STEP-UP" else None,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=15)
        )
        db.add(intent)
        db.flush()

        # Risk Assessment Record
        ra = RiskAssessment(
            id=f"ra_{uuid.uuid4().hex[:12]}",
            payment_intent_id=intent.id,
            intent_score=risk_output.intent_score,
            behavioral_score=risk_output.behavioral_score,
            provenance_score=risk_output.provenance_score,
            merchant_score=risk_output.merchant_score,
            overall_risk=risk_output.overall_risk,
            risk_score=risk_output.risk_score,
            decision=risk_output.decision,
            policy_result={"allowed": policy_result.allowed, "violations": policy_result.violations},
            evidence=risk_output.evidence,
            reasons=risk_output.reasons,
            explanation=risk_output.explanation,
            created_at=datetime.utcnow()
        )
        db.add(ra)

        # Audit Event Record
        sec_event = record_security_event(
            db=db,
            agent_id=req.agent_id,
            payment_intent_id=intent.id,
            event_type="PAYMENT_EVALUATION",
            severity=risk_output.overall_risk,
            summary=f"Evaluated payment ${req.amount:.2f} for {req.merchant_name}: {risk_output.decision}",
            payload={
                "intent_id": intent.id,
                "decision": risk_output.decision,
                "overall_risk": risk_output.overall_risk,
                "risk_score": risk_output.risk_score,
                "amount": req.amount,
                "currency": req.currency,
                "reasons": risk_output.reasons,
                "evidence": risk_output.evidence
            }
        )
        db.commit()

    # 13. Build Interactive Decision Graph
    decision_graph = build_provenance_graph(
        user_goal=req.user_goal,
        agent_id=req.agent_id,
        execution_steps=req.execution_steps,
        payment_request=req.dict(),
        decision=risk_output.decision
    )

    return {
        "payment_intent_id": intent_id,
        "agent_id": req.agent_id,
        "decision": risk_output.decision,
        "overall_risk": risk_output.overall_risk,
        "risk_score": risk_output.risk_score,
        "explanation": risk_output.explanation,
        "reasons": risk_output.reasons,
        "evidence": risk_output.evidence,
        "can_proceed_to_paypal": risk_output.decision == "ALLOW",
        "requires_human_approval": risk_output.decision == "STEP-UP",
        "scores": {
            "intent": risk_output.intent_score,
            "behavior": risk_output.behavioral_score,
            "provenance": risk_output.provenance_score,
            "merchant": risk_output.merchant_score,
            "risk_score": risk_output.risk_score
        },
        "decision_graph": decision_graph
    }

@router.post("/approve")
def handle_human_approval(req: HumanApprovalRequest, db: Session = Depends(get_db)):
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == req.payment_intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="Payment intent not found")

    agent = db.query(Agent).filter(Agent.id == intent.agent_id).first()

    if req.action == "APPROVE_ONCE":
        intent.approval_status = "APPROVED"
        intent.approved_by = req.approved_by
        intent.approval_scope = req.scope
        intent.status = "ALLOWED"
        intent.decision = "ALLOW"
        db.commit()

        record_security_event(
            db=db,
            agent_id=intent.agent_id,
            payment_intent_id=intent.id,
            event_type="HUMAN_APPROVAL_GRANTED",
            severity="INFO",
            summary=f"Human operator '{req.approved_by}' approved transaction {intent.id} (Scope: {req.scope})",
            payload={"intent_id": intent.id, "approved_by": req.approved_by, "scope": req.scope, "notes": req.notes}
        )

        return {"status": "APPROVED", "message": f"Payment intent {intent.id} authorized for one-time execution."}

    elif req.action == "RESTRICT_AGENT":
        intent.approval_status = "REJECTED"
        intent.status = "BLOCKED"
        if agent:
            agent.trust_state = TrustState.RESTRICTED
        db.commit()

        record_security_event(
            db=db,
            agent_id=intent.agent_id,
            payment_intent_id=intent.id,
            event_type="AGENT_RESTRICTED_BY_OPERATOR",
            severity="HIGH",
            summary=f"Operator rejected transaction and restricted agent {intent.agent_id}",
            payload={"intent_id": intent.id, "operator": req.approved_by, "notes": req.notes}
        )
        return {"status": "RESTRICTED", "message": f"Agent {intent.agent_id} privileges attenuated."}

    elif req.action == "QUARANTINE":
        intent.approval_status = "REJECTED"
        intent.status = "BLOCKED"
        if agent:
            agent.trust_state = TrustState.QUARANTINED
        db.commit()

        record_security_event(
            db=db,
            agent_id=intent.agent_id,
            payment_intent_id=intent.id,
            event_type="AGENT_QUARANTINED_BY_OPERATOR",
            severity="CRITICAL",
            summary=f"Operator quarantined agent {intent.agent_id} during step-up review",
            payload={"intent_id": intent.id, "operator": req.approved_by, "notes": req.notes}
        )
        return {"status": "QUARANTINED", "message": f"Agent {intent.agent_id} placed in emergency quarantine."}

    else:
        intent.approval_status = "REJECTED"
        intent.status = "BLOCKED"
        db.commit()
        return {"status": "REJECTED", "message": "Transaction rejected."}

@router.get("/events")
def get_security_events(limit: int = 50, db: Session = Depends(get_db)):
    events = db.query(SecurityEvent).order_by(SecurityEvent.created_at.desc(), SecurityEvent.id.desc()).limit(limit).all()
    return [
        {
            "id": e.id,
            "agent_id": e.agent_id,
            "payment_intent_id": e.payment_intent_id,
            "event_type": e.event_type,
            "severity": e.severity,
            "summary": e.summary,
            "payload": e.payload,
            "previous_hash": e.previous_hash,
            "event_hash": e.event_hash,
            "created_at": e.created_at.isoformat() if e.created_at else None
        } for e in events
    ]

@router.get("/verify-audit-chain")
def verify_audit_hash_chain(db: Session = Depends(get_db)):
    is_valid, count, reason = verify_audit_chain(db)
    return {
        "is_chain_valid": is_valid,
        "events_verified_count": count,
        "failure_reason": reason,
        "tamper_detected": not is_valid
    }

@router.get("/metrics")
def get_security_metrics(db: Session = Depends(get_db)):
    agents_count = db.query(Agent).count()
    intents = db.query(PaymentIntent).all()

    evaluated = len(intents)
    allowed = sum(1 for pi in intents if pi.decision == "ALLOW" or pi.approval_status == "APPROVED")
    step_up = sum(1 for pi in intents if pi.decision == "STEP-UP" and pi.approval_status == "PENDING")
    blocked = sum(1 for pi in intents if pi.decision in ["BLOCK", "QUARANTINE"])

    events = db.query(SecurityEvent).all()
    threats = sum(1 for e in events if e.severity in ["HIGH", "CRITICAL"])
    prompt_injections = sum(1 for e in events if "injection" in str(e.payload).lower() or "injection" in e.summary.lower())
    capability_breaches = sum(1 for e in events if "capability" in str(e.payload).lower() or "limit" in e.summary.lower())
    merchant_attacks = sum(1 for e in events if "merchant" in str(e.payload).lower())
    replays = sum(1 for e in events if "replay" in str(e.payload).lower())

    # Prevented Exposure: Sum of requested amounts for blocked/quarantined attempts
    blocked_amounts = sum(pi.amount for pi in intents if pi.decision in ["BLOCK", "QUARANTINE"])

    return {
        "agents_protected": max(agents_count, 1),
        "payments_evaluated": evaluated,
        "payments_allowed": allowed,
        "payments_requiring_approval": step_up,
        "payments_blocked": blocked,
        "threats_detected": threats,
        "threat_breakdown": {
            "prompt_injections": prompt_injections,
            "capability_escalations": capability_breaches,
            "merchant_attacks": merchant_attacks,
            "replay_attacks": replays
        },
        "blocked_attempted_transaction_value_usd": round(blocked_amounts, 2),
        "global_freeze_active": settings.GLOBAL_FREEZE,
        "shadow_mode_active": settings.SHADOW_MODE
    }

@router.post("/freeze")
def toggle_global_freeze(enable: bool, authorized_by: str = "SecOps Lead", db: Session = Depends(get_db)):
    settings.GLOBAL_FREEZE = enable
    record_security_event(
        db=db,
        agent_id=None,
        payment_intent_id=None,
        event_type="GLOBAL_FREEZE_TOGGLED",
        severity="CRITICAL" if enable else "INFO",
        summary=f"Global Kill Switch {'ACTIVATED' if enable else 'DEACTIVATED'} by {authorized_by}",
        payload={"freeze_active": enable, "authorized_by": authorized_by}
    )
    return {"global_freeze": settings.GLOBAL_FREEZE, "message": f"Kill switch is now {'ENGAGED' if enable else 'DISENGAGED'}"}

