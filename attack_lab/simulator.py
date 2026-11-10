import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from database.models import Agent, AgentPassport, Policy, PaymentIntent, RiskAssessment, SecurityEvent
from security.identity.passport import TrustState
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
from security.audit.tamper_evident_log import record_security_event
from security.enforcement.trust_state import TrustStateMachine
from attack_lab.scenarios import ATTACK_SCENARIOS

class AttackSimulator:
    """
    Executes live simulations of attack scenarios against SentinelX Zero-Trust defense engine.
    Ensures end-to-end evaluation with deterministic blocking, tamper-evident audit logs,
    and adaptive trust state transitions.
    """

    @staticmethod
    def run_simulation(
        db: Session,
        scenario_id: str,
        custom_payload: Optional[Dict[str, Any]] = None,
        target_agent_id: str = "ShoppingAgent-42"
    ) -> Dict[str, Any]:
        start_time = time.time()

        # Locate scenario
        scenario = next((s for s in ATTACK_SCENARIOS if s["id"] == scenario_id), None)
        if not scenario:
            raise ValueError(f"Unknown attack scenario '{scenario_id}'")

        # Load target agent or use default
        agent = db.query(Agent).filter(Agent.id == target_agent_id).first()
        if not agent:
            # Create default test agent if needed
            agent = Agent(
                id=target_agent_id,
                owner_id="Alice",
                name="ShoppingAgent-42",
                purpose="Autonomous e-commerce purchasing agent",
                status="ACTIVE",
                trust_state="TRUSTED",
                public_key="00" * 32,
                passport_version=1,
                capabilities=["search_products", "cart_management", "initiate_merchant_payments"]
            )
            db.add(agent)
            db.commit()
            db.refresh(agent)

        user_goal = scenario.get("user_goal", "Buy an SSD under $150")
        agent_req = dict(scenario["agent_request"])
        if custom_payload:
            agent_req.update(custom_payload)

        execution_steps = scenario.get("execution_steps", [])

        # 1. Nonce and Replay Check
        nonce = f"nonce_{uuid.uuid4().hex[:10]}"
        is_replay = agent_req.get("simulate_replay", False)
        if is_replay:
            # Force replay simulation by validating same nonce twice
            fixed_nonce = "fixed_replay_nonce_xyz123"
            nonce_store.validate_and_record_nonce(fixed_nonce, datetime.utcnow().isoformat())
            replay_valid, replay_msg = nonce_store.validate_and_record_nonce(fixed_nonce, datetime.utcnow().isoformat())
        else:
            replay_valid, replay_msg = nonce_store.validate_and_record_nonce(nonce, datetime.utcnow().isoformat())

        # 2. Velocity Check
        is_flood = agent_req.get("simulate_velocity_flood", False)
        velocity_count = 35 if is_flood else nonce_store.record_agent_request(target_agent_id)

        # 3. Instruction Provenance Tracking
        prov_score = ProvenanceTracker.calculate_provenance_score(execution_steps)

        # 4. Intent Drift Detection
        expected_intent = IntentAnalyzer.extract_expected_intent(user_goal)
        drift_report = IntentDriftDetector.detect_drift(expected_intent, agent_req, execution_steps)

        # 5. Behavioral Baseline Evaluation
        fingerprint = AgentBehavioralFingerprint(agent_id=target_agent_id)
        behavior_result = BehaviorAnalyzer.evaluate_behavior(
            fingerprint=fingerprint,
            amount=agent_req["amount"],
            category=agent_req["category"],
            merchant_id=agent_req["merchant_id"],
            merchant_country=agent_req.get("merchant_country", "US")
        )

        # 6. Merchant Security & Destination Binding
        is_dest_valid, is_new_merch, merch_trust_score, merch_anomalies = MerchantSecurityService.verify_merchant(
            merchant_id=agent_req["merchant_id"],
            merchant_name=agent_req["merchant_name"],
            category=agent_req["category"],
            expected_merchant_id=agent_req.get("expected_merchant_id")
        )

        # 7. Deterministic Policy Evaluation
        policy_def = PolicyDefinition(
            agent_id=target_agent_id,
            version=1,
            spending_limits=SpendingLimits(
                max_transaction=500.0,
                daily_limit=1500.0
            ),
            categories=CategoryPolicy(
                allow=["electronics", "books"],
                deny=["cryptocurrency", "gift cards"]
            ),
            allowed_countries=["US", "IN", "GB", "EU", "CA"],
            allowed_currencies=["USD", "EUR", "GBP"],
            approval=ApprovalRules(
                amount=300.0,
                new_merchant=True,
                recurring=True,
                max_quantity=5
            )
        )

        prior_spend = float(agent_req.get("simulate_high_prior_daily_spend", 0.0))
        policy_result = PolicyEngine.evaluate(
            policy=policy_def,
            amount=agent_req["amount"],
            currency=agent_req.get("currency", "USD"),
            category=agent_req["category"],
            merchant_id=agent_req["merchant_id"],
            merchant_country=agent_req.get("merchant_country", "US"),
            is_new_merchant=is_new_merch,
            quantity=agent_req.get("quantity", 1),
            is_recurring=agent_req.get("is_recurring", False),
            current_daily_spend=prior_spend
        )

        # 8. Risk Engine Synthesis
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
            agent_id=target_agent_id,
            amount=agent_req["amount"],
            merchant_name=agent_req["merchant_name"]
        )

        # 9. Adaptive State Transition & Quarantine
        if risk_output.decision == "QUARANTINE" or (risk_output.overall_risk == "CRITICAL" and risk_output.decision == "BLOCK"):
            agent.trust_state = TrustState.QUARANTINED
            db.commit()
        elif risk_output.decision == "RESTRICT":
            agent.trust_state = TrustState.RESTRICTED
            db.commit()

        # 10. Record Tamper-Evident Audit Event
        intent_id = f"pi_sim_{uuid.uuid4().hex[:10]}"
        audit_event = record_security_event(
            db=db,
            agent_id=target_agent_id,
            payment_intent_id=intent_id,
            event_type="ATTACK_SIMULATION_INTERCEPTED" if risk_output.decision in ["BLOCK", "QUARANTINE"] else "PAYMENT_EVALUATION",
            severity=risk_output.overall_risk,
            summary=f"Attack Simulation '{scenario['name']}': Decision {risk_output.decision}",
            payload={
                "scenario_id": scenario_id,
                "scenario_name": scenario["name"],
                "decision": risk_output.decision,
                "overall_risk": risk_output.overall_risk,
                "risk_score": risk_output.risk_score,
                "requested_amount": agent_req["amount"],
                "currency": agent_req.get("currency", "USD"),
                "reasons": risk_output.reasons,
                "evidence": risk_output.evidence,
                "execution_time_ms": round((time.time() - start_time) * 1000, 2)
            }
        )

        # 11. Build Decision Graph
        graph = build_provenance_graph(
            user_goal=user_goal,
            agent_id=target_agent_id,
            execution_steps=execution_steps,
            payment_request=agent_req,
            decision=risk_output.decision
        )

        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "simulation_id": f"sim_{uuid.uuid4().hex[:12]}",
            "scenario_id": scenario_id,
            "scenario_name": scenario["name"],
            "category": scenario["category"],
            "decision": risk_output.decision,
            "overall_risk": risk_output.overall_risk,
            "risk_score": risk_output.risk_score,
            "blocked_before_paypal": risk_output.decision in ["BLOCK", "QUARANTINE"],
            "new_agent_trust_state": agent.trust_state,
            "explanation": risk_output.explanation,
            "reasons": risk_output.reasons,
            "evidence": risk_output.evidence,
            "scores": {
                "intent": risk_output.intent_score,
                "behavior": risk_output.behavioral_score,
                "provenance": risk_output.provenance_score,
                "merchant": risk_output.merchant_score,
                "risk_score": risk_output.risk_score
            },
            "audit_event_id": audit_event.id,
            "audit_event_hash": audit_event.event_hash,
            "decision_graph": graph,
            "elapsed_ms": elapsed_ms
        }

