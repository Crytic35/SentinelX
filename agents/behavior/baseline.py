import math
from typing import Dict, Any, List, Optional

class AgentBehavioralFingerprint:
    def __init__(
        self,
        agent_id: str,
        median_amount: float = 96.0,
        p95_amount: float = 250.0,
        normal_categories: Optional[List[str]] = None,
        normal_merchants: Optional[List[str]] = None,
        normal_countries: Optional[List[str]] = None,
        transactions_analyzed: int = 42
    ):
        self.agent_id = agent_id
        self.median_amount = median_amount
        self.p95_amount = p95_amount
        self.normal_categories = [c.lower() for c in (normal_categories or ["electronics", "books"])]
        self.normal_merchants = normal_merchants or ["merch_bestbuy_01", "merch_newegg_02", "merch_barnesnoble_03"]
        self.normal_countries = normal_countries or ["US", "IN"]
        self.transactions_analyzed = transactions_analyzed

class BehaviorAnalyzer:
    """
    Evaluates current transaction parameters against an agent's historical behavioral baseline.
    Produces an anomaly score (0-100, where 100 is completely normal and 0 is extreme anomaly).
    """

    @staticmethod
    def evaluate_behavior(
        fingerprint: AgentBehavioralFingerprint,
        amount: float,
        category: str,
        merchant_id: str,
        merchant_country: str = "US"
    ) -> Dict[str, Any]:
        anomalies: List[str] = []
        behavior_score = 100.0

        # Amount anomaly ratio
        ratio = amount / max(fingerprint.median_amount, 1.0)
        if ratio > 10.0:  # e.g., $4,800 vs $96 is 50x
            penalty = min(70.0, ratio * 2.0)
            behavior_score -= penalty
            anomalies.append(f"Transaction amount (${amount:.2f}) is {ratio:.1f}x higher than historical median (${fingerprint.median_amount:.2f})")
        elif amount > fingerprint.p95_amount * 1.5:
            behavior_score -= 25.0
            anomalies.append(f"Amount (${amount:.2f}) exceeds historical 95th percentile (${fingerprint.p95_amount:.2f})")

        # Category novelty
        if category.lower() not in fingerprint.normal_categories:
            behavior_score -= 20.0
            anomalies.append(f"Category '{category}' has never been purchased by this agent historically")

        # Merchant novelty
        if merchant_id not in fingerprint.normal_merchants:
            behavior_score -= 15.0
            anomalies.append(f"Merchant '{merchant_id}' is an unfamiliar counterpart for this agent")

        # Country anomaly
        if merchant_country.upper() not in [c.upper() for c in fingerprint.normal_countries]:
            behavior_score -= 25.0
            anomalies.append(f"Merchant geographic origin '{merchant_country}' diverges from agent normal profile")

        final_score = max(0.0, min(100.0, round(behavior_score, 1)))
        
        status = "NORMAL"
        if final_score < 35.0:
            status = "EXTREME_ANOMALY"
        elif final_score < 65.0:
            status = "SUSPICIOUS_ANOMALY"
        elif final_score < 85.0:
            status = "SLIGHT_DEVIATION"

        return {
            "behavior_score": final_score,
            "status": status,
            "anomalies": anomalies,
            "fingerprint": {
                "median_amount": fingerprint.median_amount,
                "p95_amount": fingerprint.p95_amount,
                "transactions_analyzed": fingerprint.transactions_analyzed
            }
        }

