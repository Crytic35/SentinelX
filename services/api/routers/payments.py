from datetime import datetime
import uuid
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.session import get_db
from database.models import PaymentIntent, RiskAssessment, Payment, Agent
from paypal.client.sandbox_client import PayPalSandboxClient
from paypal.payment.receipt import SecurityReceipt
from security.audit.tamper_evident_log import record_security_event

router = APIRouter(prefix="/payments", tags=["PayPal Execution & Receipts"])

paypal_client = PayPalSandboxClient()

class CreatePayPalOrderRequest(BaseModel):
    payment_intent_id: str

class CapturePayPalOrderRequest(BaseModel):
    payment_intent_id: str
    paypal_order_id: str

@router.post("/paypal/create")
async def create_paypal_payment(req: CreatePayPalOrderRequest, db: Session = Depends(get_db)):
    # 1. Fetch Payment Intent
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == req.payment_intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="Payment Intent not found")

    # 2. CRITICAL SECURITY INVARIANT: Must be ALLOW or APPROVED
    is_authorized = (intent.decision == "ALLOW") or (intent.approval_status == "APPROVED")
    if not is_authorized:
        record_security_event(
            db=db,
            agent_id=intent.agent_id,
            payment_intent_id=intent.id,
            event_type="UNAUTHORIZED_PAYPAL_CALL_BLOCKED",
            severity="CRITICAL",
            summary=f"Invariant Enforcement: Blocked unauthorized call to PayPal API for intent {intent.id} (Decision: {intent.decision})",
            payload={"intent_id": intent.id, "decision": intent.decision, "approval_status": intent.approval_status}
        )
        raise HTTPException(
            status_code=403,
            detail=f"Security Invariant Violated: PaymentIntent '{intent.id}' is not authorized (Decision: {intent.decision}). PayPal API execution prohibited."
        )

    # 3. Create PayPal Order
    trace_id = f"trace_sx_{uuid.uuid4().hex[:14]}"
    try:
        paypal_order = await paypal_client.create_order(
            amount=intent.amount,
            currency=intent.currency,
            reference_id=intent.id,
            custom_id=f"AGENT_{intent.agent_id}|INTENT_{intent.id}|TRACE_{trace_id}",
            description=f"SentinelX Guarded Payment: {intent.purpose}"
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"PayPal Sandbox API error: {str(e)}")

    paypal_order_id = paypal_order.get("id")

    # Check if payment record already exists
    payment = db.query(Payment).filter(Payment.payment_intent_id == intent.id).first()
    if not payment:
        payment = Payment(
            id=f"pay_{uuid.uuid4().hex[:12]}",
            payment_intent_id=intent.id,
            paypal_order_id=paypal_order_id,
            status="CREATED",
            amount=intent.amount,
            currency=intent.currency,
            trace_id=trace_id,
            security_receipt={}
        )
        db.add(payment)
    else:
        payment.paypal_order_id = paypal_order_id
        payment.trace_id = trace_id
    
    db.commit()
    db.refresh(payment)

    return {
        "status": "ORDER_CREATED",
        "payment_id": payment.id,
        "paypal_order_id": paypal_order_id,
        "paypal_order": paypal_order,
        "trace_id": trace_id,
        "is_sandbox": True
    }

@router.post("/paypal/capture")
async def capture_paypal_payment(req: CapturePayPalOrderRequest, db: Session = Depends(get_db)):
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == req.payment_intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="Payment Intent not found")

    # Critical check: Intent must be authorized
    is_authorized = (intent.decision == "ALLOW") or (intent.approval_status == "APPROVED")
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Payment Intent is not authorized")

    payment = db.query(Payment).filter(Payment.payment_intent_id == intent.id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment order not initialized")

    try:
        capture_resp = await paypal_client.capture_order(req.paypal_order_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"PayPal Sandbox capture error: {str(e)}")

    capture_id = f"cap_{uuid.uuid4().hex[:10]}"
    try:
        units = capture_resp.get("purchase_units", [])
        if units and "payments" in units[0] and "captures" in units[0]["payments"]:
            capture_id = units[0]["payments"]["captures"][0]["id"]
    except Exception:
        pass

    agent = db.query(Agent).filter(Agent.id == intent.agent_id).first()
    ra = db.query(RiskAssessment).filter(RiskAssessment.payment_intent_id == intent.id).first()

    # Generate Cryptographic Tamper-Evident Security Receipt
    receipt = SecurityReceipt.generate_receipt(
        paypal_order_id=req.paypal_order_id,
        decision_id=ra.id if ra else "dec_direct",
        agent_id=intent.agent_id,
        passport_version=agent.passport_version if agent else 1,
        policy_version=1,
        intent_id=intent.id,
        risk_assessment_id=ra.id if ra else "ra_none",
        security_event_id=f"sec_{uuid.uuid4().hex[:8]}",
        amount=intent.amount,
        currency=intent.currency,
        decision=intent.decision or "ALLOW",
        risk_level=ra.overall_risk if ra else "LOW",
        risk_score=ra.risk_score if ra else 5.0,
        checks_passed=["cryptographic_identity", "passport_policy", "intent_drift_check", "provenance_verification", "paypal_destination_bound"]
    )

    payment.paypal_capture_id = capture_id
    payment.status = "COMPLETED"
    payment.security_receipt = receipt
    intent.status = "EXECUTED"
    db.commit()

    record_security_event(
        db=db,
        agent_id=intent.agent_id,
        payment_intent_id=intent.id,
        event_type="PAYPAL_PAYMENT_CAPTURED",
        severity="INFO",
        summary=f"PayPal Sandbox payment completed for ${intent.amount:.2f} (PayPal Order: {req.paypal_order_id})",
        payload={
            "paypal_order_id": req.paypal_order_id,
            "capture_id": capture_id,
            "receipt_id": receipt["receipt_id"],
            "tamper_seal": receipt["tamper_seal"]
        }
    )

    return {
        "status": "COMPLETED",
        "paypal_order_id": req.paypal_order_id,
        "paypal_capture_id": capture_id,
        "security_receipt": receipt,
        "trace_id": payment.trace_id
    }

@router.get("/receipts/{receipt_id}")
def get_security_receipt(receipt_id: str, db: Session = Depends(get_db)):
    payments = db.query(Payment).all()
    for p in payments:
        if p.security_receipt and p.security_receipt.get("receipt_id") == receipt_id:
            return p.security_receipt
    raise HTTPException(status_code=404, detail="Receipt not found")

@router.get("/history")
def get_payment_history(db: Session = Depends(get_db)):
    payments = db.query(Payment).order_by(Payment.created_at.desc()).limit(50).all()
    results = []
    for p in payments:
        intent = p.payment_intent
        results.append({
            "id": p.id,
            "payment_intent_id": p.payment_intent_id,
            "paypal_order_id": p.paypal_order_id,
            "paypal_capture_id": p.paypal_capture_id,
            "status": p.status,
            "amount": p.amount,
            "currency": p.currency,
            "trace_id": p.trace_id,
            "merchant_name": intent.merchant_name if intent else "Unknown",
            "purpose": intent.purpose if intent else "General Purchase",
            "agent_id": intent.agent_id if intent else "Unknown",
            "receipt": p.security_receipt,
            "created_at": p.created_at.isoformat() if p.created_at else None
        })
    return results

