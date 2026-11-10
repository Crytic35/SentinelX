from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

class ProvenanceSourceType:
    USER = "USER"
    SYSTEM_POLICY = "SYSTEM_POLICY"
    SIGNED_TOOL = "SIGNED_TOOL"
    KNOWN_API = "KNOWN_API"
    WEBPAGE = "WEBPAGE"
    UNKNOWN_TOOL = "UNKNOWN_TOOL"
    UNVERIFIED_MCP_TOOL = "UNVERIFIED_MCP_TOOL"

SOURCE_TRUST_RATINGS = {
    ProvenanceSourceType.USER: 100.0,
    ProvenanceSourceType.SYSTEM_POLICY: 100.0,
    ProvenanceSourceType.SIGNED_TOOL: 95.0,
    ProvenanceSourceType.KNOWN_API: 90.0,
    ProvenanceSourceType.WEBPAGE: 30.0,
    ProvenanceSourceType.UNKNOWN_TOOL: 20.0,
    ProvenanceSourceType.UNVERIFIED_MCP_TOOL: 15.0,
}

class ProvenanceNode:
    def __init__(
        self,
        node_id: str,
        source_type: str,
        description: str,
        content: str,
        trust_rating: float,
        timestamp: Optional[str] = None
    ):
        self.node_id = node_id
        self.source_type = source_type
        self.description = description
        self.content = content
        self.trust_rating = trust_rating
        self.timestamp = timestamp or datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "source_type": self.source_type,
            "description": self.description,
            "content": self.content,
            "trust_rating": self.trust_rating,
            "timestamp": self.timestamp
        }

class ProvenanceTracker:
    @staticmethod
    def calculate_provenance_score(steps: List[Dict[str, Any]]) -> float:
        """
        Calculates aggregate provenance trustworthiness (0-100).
        If any instruction step originates from untrusted sources (e.g. WEBPAGE, UNKNOWN_TOOL),
        the score drops severely.
        """
        if not steps:
            return 80.0

        scores = []
        has_untrusted_override = False
        for step in steps:
            st = step.get("source_type", ProvenanceSourceType.USER)
            rating = SOURCE_TRUST_RATINGS.get(st, 25.0)
            if rating < 50.0 and step.get("is_instruction_override", False):
                has_untrusted_override = True
            scores.append(rating)

        avg_score = sum(scores) / len(scores)
        if has_untrusted_override:
            # Severe penalization for untrusted instruction modification
            return min(avg_score, 18.0)
        return round(avg_score, 1)

