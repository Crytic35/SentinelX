import uuid
from datetime import datetime
from typing import Dict, Any, List
from security.identity.crypto import canonical_json, hash_content

class SecurityReceipt:
    @staticmethod
    def generate_receipt(
        paypal_order_id: str,
        decision_id: str,
        agent_id: str,
        passport_version: int,
        policy_version: int,
        intent_id: str,
        risk_assessment_id: str,
        security_event_id: str,
        amount: float,
        currency: str,
        decision: str,
        risk_level: str,
        risk_score: float,
        checks_passed: List[str]
    ) -> Dict[str, Any]:
        receipt_id = f"rcpt_{uuid.uuid4().hex[:14]}"
        timestamp = datetime.utcnow().isoformat()

        receipt_data = {
            "receipt_id": receipt_id,
            "paypal_order_id": paypal_order_id,
            "sentinelx_decision_id": decision_id,
            "agent_id": agent_id,
            "passport_version": passport_version,
            "policy_version": policy_version,
            "intent_id": intent_id,
            "risk_assessment_id": risk_assessment_id,
            "security_event_id": security_event_id,
            "amount": amount,
            "currency": currency,
            "decision": decision,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "verification_checks_passed": checks_passed,
            "issued_at": timestamp
        }

        # Cryptographic tamper seal
        receipt_data["tamper_seal"] = hash_content(receipt_data)
        return receipt_data

