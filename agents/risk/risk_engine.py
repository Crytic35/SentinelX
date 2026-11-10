from typing import Dict, Any, List, Optional
from security.policies.engine import PolicyCheckResult
from agents.intent.drift_detector import IntentDriftReport
from security.identity.passport import TrustState

class RiskAssessmentOutput:
    def __init__(self):
        self.overall_risk: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
        self.risk_score: float = 10.0  # 0 to 100 (higher = riskier)
        self.decision: str = "ALLOW"   # ALLOW, STEP-UP, RESTRICT, BLOCK, QUARANTINE
        self.evidence: List[Dict[str, Any]] = []
        self.reasons: List[str] = []
        self.intent_score: float = 100.0
        self.behavioral_score: float = 100.0
        self.provenance_score: float = 100.0
        self.merchant_score: float = 100.0
        self.policy_violations_count: int = 0
        self.explanation: str = ""

class RiskEngine:
    """
    Synthesizes deterministic policy results, intent drift, behavioral anomalies,
    instruction provenance, and merchant verification into structured risk evidence.
    Enforces Zero-Trust boundary: The LLM does NOT make the numerical risk decision.
    """

    @staticmethod
    def evaluate(
        agent_trust_state: str,
        policy_result: PolicyCheckResult,
        intent_report: IntentDriftReport,
        behavior_result: Dict[str, Any],
        provenance_score: float,
        merchant_trust_score: float,
        merchant_anomalies: List[Dict[str, Any]],
        replay_valid: bool,
        replay_message: str,
        velocity_count_last_minute: int = 1
    ) -> RiskAssessmentOutput:
        out = RiskAssessmentOutput()

        out.intent_score = intent_report.semantic_similarity_score
        out.behavioral_score = behavior_result.get("behavior_score", 100.0)
        out.provenance_score = provenance_score
        out.merchant_score = merchant_trust_score
        out.policy_violations_count = len(policy_result.violations)

        # 1. Check Replay Attack
        if not replay_valid:
            out.overall_risk = "CRITICAL"
            out.decision = "BLOCK"
            out.risk_score = 100.0
            out.reasons.append(f"Cryptographic replay protection failure: {replay_message}")
            out.evidence.append({
                "signal": "replay_protection",
                "severity": "CRITICAL",
                "message": replay_message
            })
            return out

        # 2. Check Agent Trust State (Quarantined or Revoked agents fail instantly)
        if agent_trust_state in [TrustState.QUARANTINED, TrustState.REVOKED]:
            out.overall_risk = "CRITICAL"
            out.decision = "QUARANTINE"
            out.risk_score = 100.0
            out.reasons.append(f"Agent is in '{agent_trust_state}' state. All payment executions are halted.")
            out.evidence.append({
                "signal": "agent_trust_state",
                "severity": "CRITICAL",
                "state": agent_trust_state,
                "message": f"Agent is quarantined: cannot initiate payments"
            })
            return out

        # 3. Check Velocity Flooding
        if velocity_count_last_minute > 20:
            out.overall_risk = "CRITICAL"
            out.decision = "BLOCK"
            out.risk_score = 98.0
            out.reasons.append(f"Payment velocity flood detected ({velocity_count_last_minute} requests/min)")
            out.evidence.append({
                "signal": "velocity_protection",
                "severity": "CRITICAL",
                "requests_per_min": velocity_count_last_minute
            })
            return out

        # 4. Check Hard Policy Violations
        if not policy_result.allowed:
            out.overall_risk = "CRITICAL"
            out.decision = "BLOCK"
            out.risk_score = 95.0
            for v in policy_result.violations:
                out.reasons.append(v["message"])
                out.evidence.append({
                    "signal": "hard_policy_violation",
                    "severity": "CRITICAL",
                    "rule": v["rule"],
                    "expected": v["expected"],
                    "actual": v["actual"],
                    "message": v["message"]
                })

        # 5. Check Intent Drift
        if intent_report.drift_detected:
            for dev in intent_report.deviations:
                out.reasons.append(dev["message"])
                out.evidence.append({
                    "signal": "intent_drift",
                    "severity": "HIGH",
                    "dimension": dev["dimension"],
                    "expected": dev["expected"],
                    "actual": dev["actual"],
                    "origin": dev["origin_step"],
                    "message": dev["message"]
                })
            if out.overall_risk != "CRITICAL":
                out.overall_risk = "HIGH"
                out.decision = "BLOCK"

        # 6. Check Provenance & Tool Poisoning
        if provenance_score < 40.0:
            out.reasons.append(f"Untrusted instruction provenance (score: {provenance_score:.1f}/100)")
            out.evidence.append({
                "signal": "instruction_provenance",
                "severity": "HIGH",
                "score": provenance_score,
                "message": "Instruction originated or was mutated by untrusted external web/tool source"
            })
            if out.overall_risk not in ["CRITICAL", "HIGH"]:
                out.overall_risk = "HIGH"
                out.decision = "BLOCK"

        # 7. Check Behavioral Anomalies
        if behavior_result.get("status") == "EXTREME_ANOMALY":
            out.reasons.extend(behavior_result.get("anomalies", []))
            out.evidence.append({
                "signal": "behavioral_anomaly",
                "severity": "HIGH",
                "status": "EXTREME_ANOMALY",
                "score": out.behavioral_score,
                "details": behavior_result.get("anomalies")
            })
            if out.overall_risk not in ["CRITICAL", "HIGH"]:
                out.overall_risk = "HIGH"
                out.decision = "BLOCK"

        # 8. Check Merchant Security & Destination Binding
        for anom in merchant_anomalies:
            sev = anom.get("severity", "MEDIUM")
            out.reasons.append(anom.get("message", "Merchant security anomaly"))
            out.evidence.append({
                "signal": anom.get("signal", "merchant_anomaly"),
                "severity": sev,
                "message": anom.get("message")
            })
            if sev == "CRITICAL":
                out.overall_risk = "CRITICAL"
                out.decision = "BLOCK"

        # 9. Step-up Evaluation (If no hard blocks were triggered)
        if out.decision not in ["BLOCK", "QUARANTINE"]:
            if policy_result.requires_step_up:
                out.overall_risk = "MEDIUM" if out.overall_risk == "LOW" else out.overall_risk
                out.decision = "STEP-UP"
                for reason in policy_result.step_up_reasons:
                    out.reasons.append(reason)
            elif any(a.get("signal") == "new_merchant" for a in merchant_anomalies):
                out.overall_risk = "MEDIUM"
                out.decision = "STEP-UP"

        # Calculate final numeric risk score (0 to 100)
        # Weighted composite risk
        risk_components = [
            (100.0 - out.intent_score) * 0.35,
            (100.0 - out.behavioral_score) * 0.25,
            (100.0 - out.provenance_score) * 0.20,
            (100.0 - out.merchant_score) * 0.20
        ]
        composite = sum(risk_components)
        if out.decision in ["BLOCK", "QUARANTINE"]:
            composite = max(composite, 85.0)
        elif out.decision == "STEP-UP":
            composite = max(composite, 45.0)
        out.risk_score = round(min(100.0, max(0.0, composite)), 1)

        return out

