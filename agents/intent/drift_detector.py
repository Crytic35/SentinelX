from typing import Dict, Any, List, Optional
from agents.intent.analyzer import StructuredIntent

class IntentDriftReport:
    def __init__(self):
        self.drift_detected: bool = False
        self.drift_origin_step: Optional[str] = None
        self.drift_origin_source: Optional[str] = None
        self.semantic_similarity_score: float = 100.0  # 0 to 100
        self.deviations: List[Dict[str, Any]] = []

    def add_deviation(self, dimension: str, expected: Any, actual: Any, origin_step: str, origin_source: str, message: str):
        self.drift_detected = True
        self.drift_origin_step = self.drift_origin_step or origin_step
        self.drift_origin_source = self.drift_origin_source or origin_source
        self.deviations.append({
            "dimension": dimension,
            "expected": expected,
            "actual": actual,
            "origin_step": origin_step,
            "origin_source": origin_source,
            "message": message
        })

class IntentDriftDetector:
    """
    Detects material drift across:
    User Instruction -> Agent Plan -> Tool Outputs -> Payment Request.
    Identifies exact origin and source of deviation.
    """

    @staticmethod
    def detect_drift(
        expected_intent: StructuredIntent,
        payment_request: Dict[str, Any],
        execution_chain: Optional[List[Dict[str, Any]]] = None
    ) -> IntentDriftReport:
        report = IntentDriftReport()

        actual_amount = float(payment_request.get("amount", 0.0))
        actual_category = str(payment_request.get("category", "")).lower()
        actual_quantity = int(payment_request.get("quantity", 1))
        actual_purpose = str(payment_request.get("purpose", "")).lower()
        actual_recurring = bool(payment_request.get("is_recurring", False))

        # Check execution chain for provenance origin
        injected_step = None
        injected_source = "UNKNOWN"
        if execution_chain:
            for step in execution_chain:
                if step.get("is_malicious", False) or step.get("source_type") in ["WEBPAGE", "UNKNOWN_TOOL", "UNVERIFIED_MCP_TOOL"]:
                    injected_step = step.get("name", "External Untrusted Step")
                    injected_source = step.get("source_type", "WEBPAGE")
                    break

        default_origin_step = injected_step or "agent_plan_change"
        default_origin_source = injected_source if injected_step else "AGENT"

        # 1. Amount Drift (tolerance max +10%)
        if actual_amount > expected_intent.max_amount * 1.1:
            report.add_deviation(
                dimension="amount",
                expected=f"<=${expected_intent.max_amount:.2f}",
                actual=f"${actual_amount:.2f}",
                origin_step=default_origin_step,
                origin_source=default_origin_source,
                message=f"Requested amount ${actual_amount:.2f} significantly exceeds authorized intent maximum ${expected_intent.max_amount:.2f}"
            )
            report.semantic_similarity_score -= 40.0

        # 2. Category Drift
        if expected_intent.category.lower() != actual_category:
            report.add_deviation(
                dimension="category",
                expected=expected_intent.category,
                actual=actual_category,
                origin_step=default_origin_step,
                origin_source=default_origin_source,
                message=f"Category shifted from expected '{expected_intent.category}' to '{actual_category}'"
            )
            report.semantic_similarity_score -= 30.0

        # 3. Quantity Drift
        if actual_quantity > expected_intent.quantity:
            report.add_deviation(
                dimension="quantity",
                expected=expected_intent.quantity,
                actual=actual_quantity,
                origin_step=default_origin_step,
                origin_source=default_origin_source,
                message=f"Item quantity manipulated from {expected_intent.quantity} to {actual_quantity}"
            )
            report.semantic_similarity_score -= 25.0

        # 4. Recurring Conversion Drift (One-time to Subscription)
        if actual_recurring:
            report.add_deviation(
                dimension="billing_frequency",
                expected="one-time",
                actual="recurring_subscription",
                origin_step=default_origin_step,
                origin_source=default_origin_source,
                message="Transaction was covertly converted to a recurring subscription"
            )
            report.semantic_similarity_score -= 35.0

        report.semantic_similarity_score = max(0.0, round(report.semantic_similarity_score, 1))
        return report

