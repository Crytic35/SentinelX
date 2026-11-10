from typing import Dict, Any, List
from agents.risk.risk_engine import RiskAssessmentOutput

class ExplainableRiskService:
    """
    Synthesizes human-readable cybersecurity explanations strictly from structured evidence.
    Ensures complete transparency for operators and auditors.
    """

    @staticmethod
    def generate_explanation(assessment: RiskAssessmentOutput, agent_id: str, amount: float, merchant_name: str) -> str:
        if assessment.decision == "ALLOW":
            return (
                f"Transaction of ${amount:.2f} to {merchant_name} by agent '{agent_id}' was verified and ALLOWED. "
                f"Agent identity and passport signature are valid. Deterministic spending policy checks passed. "
                f"Behavior aligns with historical profile (score: {assessment.behavioral_score:.1f}/100), and "
                f"instruction provenance is authenticated."
            )

        if assessment.decision == "STEP-UP":
            reasons_text = "; ".join(assessment.reasons)
            return (
                f"Transaction of ${amount:.2f} to {merchant_name} requires HUMAN APPROVAL (STEP-UP). "
                f"Reason: {reasons_text}. The transaction does not violate hard security boundaries, but triggers "
                f"risk policies requiring human operator sign-off before payment dispatch."
            )

        if assessment.decision in ["BLOCK", "QUARANTINE"]:
            reasons_text = "; ".join(assessment.reasons)
            return (
                f"CRITICAL SECURITY ENFORCEMENT: Payment of ${amount:.2f} to {merchant_name} was BLOCKED before execution. "
                f"Threat indicators detected: {reasons_text}. In accordance with SentinelX Zero-Trust policy, "
                f"execution has been halted immediately to safeguard financial integrity. Agent '{agent_id}' trust state "
                f"transitioned to {assessment.decision}."
            )

        return f"SentinelX evaluated transaction with decision '{assessment.decision}'."

