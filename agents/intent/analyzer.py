import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class StructuredIntent(BaseModel):
    purpose: str
    max_amount: float
    currency: str = "USD"
    category: str
    quantity: int = 1
    merchant_constraints: List[str] = Field(default_factory=list)
    user_approval_required: bool = False
    drift_detected: bool = False
    drift_reasons: List[str] = Field(default_factory=list)

class IntentAnalyzer:
    """
    Analyzes agent goals, execution context, and compares against payment request.
    Uses strict schema validation and deterministic boundary verification.
    """

    @staticmethod
    def extract_expected_intent(user_goal: str) -> StructuredIntent:
        """
        Extracts structured baseline intent from user instructions.
        Uses deterministic semantic heuristics and boundary extraction.
        """
        goal_lower = user_goal.lower()

        # Extract amount
        amt_match = re.search(r'(?:under|less than|up to|max(?:imum)? of|\$)\s*\$?([0-9,]+(?:\.[0-9]+)?)', goal_lower)
        max_amount = 150.0
        if amt_match:
            try:
                max_amount = float(amt_match.group(1).replace(',', ''))
            except ValueError:
                pass

        # Extract quantity
        qty_match = re.search(r'\b([0-9]+)\s+(?:items|units|copies|x|ssds|gpus|books)', goal_lower)
        quantity = int(qty_match.group(1)) if qty_match else 1

        # Extract category
        category = "electronics"
        if "book" in goal_lower:
            category = "books"
        elif "grocery" in goal_lower or "food" in goal_lower:
            category = "groceries"
        elif "crypto" in goal_lower or "bitcoin" in goal_lower:
            category = "cryptocurrency"
        elif "gift card" in goal_lower:
            category = "gift cards"

        # Extract purpose
        purpose = user_goal.strip()

        return StructuredIntent(
            purpose=purpose,
            max_amount=max_amount,
            currency="USD",
            category=category,
            quantity=quantity,
            merchant_constraints=[],
            user_approval_required=False
        )

