import re
from typing import Dict, Any, Optional, Tuple
from security.policies.schema import PolicyDefinition, SpendingLimits, CategoryPolicy, ApprovalRules

def parse_natural_language_policy(nl_text: str, agent_id: str = "ShoppingAgent-42") -> Tuple[Optional[PolicyDefinition], Optional[str]]:
    """
    Parses a natural language policy prompt into a strictly validated PolicyDefinition.
    Includes deterministic rule extractor with schema validation.
    """
    text = nl_text.lower()

    # Default baseline
    max_tx = 500.0
    daily_lim = 1500.0
    approval_amt = 300.0
    allowed_cats = ["electronics", "books"]
    blocked_cats = ["cryptocurrency", "gift cards"]

    # Match max transaction / spend up to
    spend_match = re.search(r'(?:spend up to|limit of|maximum of|max(?:imum)? transaction.*?)\$?([0-9,]+(?:\.[0-9]+)?)', text)
    if spend_match:
        try:
            max_tx = float(spend_match.group(1).replace(',', ''))
            daily_lim = max_tx * 3.0  # sensible default ratio
        except ValueError:
            pass

    # Match daily limit
    daily_match = re.search(r'(?:daily limit of|up to)\$?([0-9,]+(?:\.[0-9]+)?)\s*(?:a day|daily|per day)', text)
    if daily_match:
        try:
            daily_lim = float(daily_match.group(1).replace(',', ''))
        except ValueError:
            pass

    # Match approval threshold
    approval_match = re.search(r'(?:require approval (?:above|over)|approval threshold.*?)\$?([0-9,]+(?:\.[0-9]+)?)', text)
    if approval_match:
        try:
            approval_amt = float(approval_match.group(1).replace(',', ''))
        except ValueError:
            pass
    else:
        approval_amt = min(max_tx * 0.6, 300.0)

    # Categories
    known_cats = ["electronics", "books", "groceries", "apparel", "hardware", "software", "office supplies", "travel"]
    detected_allowed = [c for c in known_cats if c in text]
    if detected_allowed:
        allowed_cats = detected_allowed

    # Denied categories
    known_denied = ["cryptocurrency", "crypto", "gift cards", "gambling", "adult", "weapons"]
    detected_denied = [c for c in known_denied if c in text]
    if detected_denied:
        blocked_cats = detected_denied

    # Conflict check: ensure approval threshold <= max transaction
    if approval_amt > max_tx:
        return None, f"Policy conflict: Approval threshold (${approval_amt:.2f}) cannot be greater than maximum transaction limit (${max_tx:.2f})"

    # Conflict check: ensure allowed and blocked categories do not intersect
    intersection = set(allowed_cats).intersection(set(blocked_cats))
    if intersection:
        return None, f"Policy conflict: Category '{next(iter(intersection))}' cannot be both allowed and blocked"

    try:
        policy = PolicyDefinition(
            agent_id=agent_id,
            version=1,
            spending_limits=SpendingLimits(
                max_transaction=max_tx,
                daily_limit=daily_lim
            ),
            categories=CategoryPolicy(
                allow=allowed_cats,
                deny=blocked_cats
            ),
            allowed_countries=["US", "IN", "GB", "EU", "CA"],
            allowed_currencies=["USD", "EUR", "GBP"],
            approval=ApprovalRules(
                amount=approval_amt,
                new_merchant=True,
                recurring=True,
                max_quantity=5
            )
        )
        return policy, None
    except Exception as e:
        return None, f"Schema validation error: {str(e)}"

