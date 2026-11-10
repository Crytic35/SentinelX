from typing import Dict, Any, List, Optional

NORMAL_SHOPPING_SEQUENCE = [
    "search_products",
    "compare_products",
    "add_to_cart",
    "initiate_checkout",
    "request_payment"
]

SUSPICIOUS_KEYWORDS = [
    "ignore previous instructions",
    "system update",
    "urgent override",
    "admin mode",
    "transfer immediately",
    "send payment to",
    "gift card code",
    "bypass sentinelx",
    "increase limit",
    "elevate privileges"
]

class SequenceAnomalyDetector:
    """
    Analyzes transaction and action sequences to detect prompt injections,
    hijacked goals, and uncharacteristic jumps in execution flow.
    """

    @staticmethod
    def analyze_sequence(steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        detected_injections: List[Dict[str, Any]] = []
        abnormal_steps: List[str] = []

        for idx, step in enumerate(steps):
            content = str(step.get("content", "")).lower()
            name = str(step.get("name", f"Step {idx+1}"))
            source_type = step.get("source_type", "UNKNOWN")

            # Check prompt injection signatures
            for kw in SUSPICIOUS_KEYWORDS:
                if kw in content:
                    detected_injections.append({
                        "step_index": idx,
                        "step_name": name,
                        "matched_signature": kw,
                        "source_type": source_type,
                        "snippet": content[:120]
                    })
                    break

            # Check untrusted instruction overrides
            if source_type in ["WEBPAGE", "UNKNOWN_TOOL", "UNVERIFIED_MCP_TOOL"] and step.get("is_instruction_override", False):
                abnormal_steps.append(f"Untrusted step '{name}' ({source_type}) attempted to override agent objective")

        is_anomalous = len(detected_injections) > 0 or len(abnormal_steps) > 0
        sequence_confidence = 10.0 if detected_injections else (40.0 if abnormal_steps else 98.0)

        return {
            "is_anomalous": is_anomalous,
            "sequence_confidence": sequence_confidence,
            "detected_injections": detected_injections,
            "abnormal_steps": abnormal_steps
        }

