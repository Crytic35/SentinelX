from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from security.policies.schema import PolicyDefinition

class PolicyCheckResult:
    def __init__(self):
        self.allowed: bool = True
        self.requires_step_up: bool = False
        self.violations: List[Dict[str, Any]] = []
        self.step_up_reasons: List[str] = []
        self.evidence: List[Dict[str, Any]] = []
        self.decision: str = "ALLOW"  # ALLOW, STEP-UP, BLOCK

    def add_violation(self, rule: str, expected: Any, actual: Any, message: str):
        self.allowed = False
        self.decision = "BLOCK"
        self.violations.append({
            "rule": rule,
            "expected": expected,
            "actual": actual,
            "message": message
        })
        self.evidence.append({
            "signal": "capability_violation",
            "rule": rule,
            "expected": expected,
            "actual": actual,
            "status": "FAIL"
        })

    def add_step_up(self, reason: str, details: Dict[str, Any]):
        self.requires_step_up = True
        if self.decision != "BLOCK":
            self.decision = "STEP-UP"
        self.step_up_reasons.append(reason)
        self.evidence.append({
            "signal": "approval_threshold",
            "reason": reason,
            "details": details,
            "status": "STEP_UP"
        })

    def add_pass(self, rule: str, details: Any):
        self.evidence.append({
            "signal": "policy_check",
            "rule": rule,
            "details": details,
            "status": "PASS"
        })


class PolicyEngine:
    """
    Deterministic Policy Engine for SentinelX.
    Enforces spending limits, categories, geography, currencies, merchants, and approval thresholds.
    Strictly fail-closed: if policy is missing or contradictory, blocks payment.
    """

    @staticmethod
    def evaluate(
        policy: PolicyDefinition,
        amount: float,
        currency: str,
        category: str,
        merchant_id: str,
        merchant_country: str,
        is_new_merchant: bool,
        quantity: int,
        is_recurring: bool,
        current_daily_spend: float = 0.0,
        merchant_is_blocked: bool = False
    ) -> PolicyCheckResult:
        result = PolicyCheckResult()

        category_clean = category.lower().strip()

        # 1. Blocked Merchants
        if merchant_is_blocked or merchant_id in policy.blocked_merchants:
            result.add_violation(
                rule="blocked_merchant",
                expected="merchant not in blocklist",
                actual=merchant_id,
                message=f"Merchant '{merchant_id}' is explicitly blocked by security policy"
            )

        # 2. Category Denylist (Always takes precedence)
        denied_categories = [c.lower().strip() for c in policy.categories.deny]
        if category_clean in denied_categories:
            result.add_violation(
                rule="blocked_category",
                expected=f"not in {denied_categories}",
                actual=category_clean,
                message=f"Category '{category}' is explicitly forbidden"
            )

        # 3. Category Allowlist
        allowed_categories = [c.lower().strip() for c in policy.categories.allow]
        if allowed_categories and category_clean not in allowed_categories:
            result.add_violation(
                rule="allowed_categories",
                expected=allowed_categories,
                actual=category_clean,
                message=f"Category '{category}' is not in authorized category allowlist"
            )
        else:
            result.add_pass("category_check", category_clean)

        # 4. Maximum Transaction Amount
        if amount > policy.spending_limits.max_transaction:
            result.add_violation(
                rule="max_transaction_limit",
                expected=policy.spending_limits.max_transaction,
                actual=amount,
                message=f"Requested amount ${amount:.2f} exceeds per-transaction limit of ${policy.spending_limits.max_transaction:.2f}"
            )
        else:
            result.add_pass("max_transaction_limit", {"limit": policy.spending_limits.max_transaction, "actual": amount})

        # 5. Daily Cumulative Spending Limit
        projected_daily = current_daily_spend + amount
        if projected_daily > policy.spending_limits.daily_limit:
            result.add_violation(
                rule="daily_spending_limit",
                expected=policy.spending_limits.daily_limit,
                actual=projected_daily,
                message=f"Projected daily spend ${projected_daily:.2f} exceeds daily ceiling of ${policy.spending_limits.daily_limit:.2f} (current: ${current_daily_spend:.2f})"
            )
        else:
            result.add_pass("daily_spending_limit", {"limit": policy.spending_limits.daily_limit, "projected": projected_daily})

        # 6. Currency Verification
        if currency.upper() not in [c.upper() for c in policy.allowed_currencies]:
            result.add_violation(
                rule="allowed_currencies",
                expected=policy.allowed_currencies,
                actual=currency,
                message=f"Currency '{currency}' is not authorized"
            )
        else:
            result.add_pass("currency_check", currency)

        # 7. Country / Geographic Restrictions
        if merchant_country.upper() not in [c.upper() for c in policy.allowed_countries]:
            result.add_violation(
                rule="allowed_countries",
                expected=policy.allowed_countries,
                actual=merchant_country,
                message=f"Merchant country '{merchant_country}' is outside authorized geographic boundaries"
            )
        else:
            result.add_pass("geographic_check", merchant_country)

        # 8. Quantity Restrictions
        if quantity > policy.approval.max_quantity:
            result.add_violation(
                rule="max_quantity",
                expected=policy.approval.max_quantity,
                actual=quantity,
                message=f"Requested item quantity ({quantity}) exceeds maximum allowed ({policy.approval.max_quantity})"
            )
        else:
            result.add_pass("quantity_check", quantity)

        # 9. Recurring / Subscription Checks
        if is_recurring:
            if not policy.allow_subscriptions:
                # If subscriptions are not explicitly allowed, require step-up or block
                result.add_step_up(
                    "Recurring subscription purchase detected",
                    {"recurring": True, "policy_allow_subscriptions": False}
                )
            elif policy.approval.recurring:
                result.add_step_up(
                    "Policy mandates human approval for all recurring subscriptions",
                    {"recurring": True}
                )

        # 10. Human Approval Thresholds (Step-up conditions if no hard violations)
        if amount > policy.approval.amount:
            result.add_step_up(
                f"Transaction amount ${amount:.2f} exceeds approval threshold of ${policy.approval.amount:.2f}",
                {"threshold": policy.approval.amount, "actual": amount}
            )

        # 11. New Merchant Approval
        if is_new_merchant and policy.approval.new_merchant:
            result.add_step_up(
                f"Merchant '{merchant_id}' is newly encountered; human review required by policy",
                {"merchant_id": merchant_id, "is_new": True}
            )

        return result

