"""
SentinelX Python SDK
Zero-Trust Security Gateway for Autonomous Payment Agents
"""

from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime

from security.policies.schema import PolicyDefinition, SpendingLimits, CategoryPolicy, ApprovalRules
from security.policies.engine import PolicyEngine, PolicyCheckResult
from security.replay.nonce_store import nonce_store
from security.provenance.tracker import ProvenanceTracker
from security.merchant.registry import MerchantSecurityService
from agents.intent.analyzer import IntentAnalyzer
from agents.intent.drift_detector import IntentDriftDetector
from agents.behavior.baseline import BehaviorAnalyzer, AgentBehavioralFingerprint
from agents.risk.risk_engine import RiskEngine, RiskAssessmentOutput
from agents.risk.explainable import ExplainableRiskService

class PaymentGuard:
    """
    Client-side or middleware wrapper for SentinelX Zero-Trust authorization.
    Protects PayPal execution by evaluating intent, provenance, policy, and behavior
    before money moves.
    """

    def __init__(self, agent_id: str, public_key: Optional[str] = None):
        self.agent_id = agent_id
        self.public_key = public_key

    def authorize(
        self,
        payment_request: Dict[str, Any],
        user_goal: Optional[str] = None,
        execution_steps: Optional[List[Dict[str, Any]]] = None
    ) -> RiskAssessmentOutput:
        amount = float(payment_request.get("amount", 0.0))
        currency = str(payment_request.get("currency", "USD"))
        category = str(payment_request.get("category", "general"))
        merchant_id = str(payment_request.get("merchant_id", "unknown"))
        merchant_name = str(payment_request.get("merchant_name", "Unknown Merchant"))
        merchant_country = str(payment_request.get("merchant_country", "US"))
        is_recurring = bool(payment_request.get("is_recurring", False))
        quantity = int(payment_request.get("quantity", 1))

        # Replay and Nonce check
        nonce = payment_request.get("nonce", f"sdk_nonce_{uuid.uuid4().hex[:8]}")
        timestamp = payment_request.get("timestamp", datetime.utcnow().isoformat())
        replay_valid, replay_msg = nonce_store.validate_and_record_nonce(nonce, timestamp)
        velocity_count = nonce_store.record_agent_request(self.agent_id)

        # Provenance
        steps = execution_steps or []
        prov_score = ProvenanceTracker.calculate_provenance_score(steps)

        # Intent Drift
        goal = user_goal or payment_request.get("purpose", "Purchase")
        expected_intent = IntentAnalyzer.extract_expected_intent(goal)
        drift = IntentDriftDetector.detect_drift(expected_intent, payment_request, steps)

        # Behavior
        fp = AgentBehavioralFingerprint(agent_id=self.agent_id)
        behav = BehaviorAnalyzer.evaluate_behavior(fp, amount, category, merchant_id, merchant_country)

        # Merchant
        is_dest_valid, is_new, merch_score, merch_anoms = MerchantSecurityService.verify_merchant(
            merchant_id=merchant_id,
            merchant_name=merchant_name,
            category=category,
            expected_merchant_id=payment_request.get("expected_merchant_id")
        )

        # Policy
        pol = PolicyDefinition(
            agent_id=self.agent_id,
            version=1,
            spending_limits=SpendingLimits(max_transaction=500.0, daily_limit=1500.0),
            categories=CategoryPolicy(allow=["electronics", "books"], deny=["cryptocurrency", "gift cards"]),
            allowed_countries=["US", "IN", "GB", "EU", "CA"],
            allowed_currencies=["USD", "EUR", "GBP"],
            approval=ApprovalRules(amount=300.0, new_merchant=True, recurring=True, max_quantity=5)
        )
        pol_res = PolicyEngine.evaluate(
            policy=pol,
            amount=amount,
            currency=currency,
            category=category,
            merchant_id=merchant_id,
            merchant_country=merchant_country,
            is_new_merchant=is_new,
            quantity=quantity,
            is_recurring=is_recurring
        )

        # Risk Synthesis
        decision = RiskEngine.evaluate(
            agent_trust_state="TRUSTED",
            policy_result=pol_res,
            intent_report=drift,
            behavior_result=behav,
            provenance_score=prov_score,
            merchant_trust_score=merch_score,
            merchant_anomalies=merch_anoms,
            replay_valid=replay_valid,
            replay_message=replay_msg,
            velocity_count_last_minute=velocity_count
        )

        decision.explanation = ExplainableRiskService.generate_explanation(decision, self.agent_id, amount, merchant_name)
        return decision

