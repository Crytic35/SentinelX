from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class SpendingLimits(BaseModel):
    max_transaction: float = Field(..., description="Hard limit per single transaction")
    daily_limit: float = Field(..., description="Hard cumulative spending limit per 24h")
    monthly_limit: Optional[float] = None

class CategoryPolicy(BaseModel):
    allow: List[str] = Field(default_factory=list, description="Explicitly allowed categories")
    deny: List[str] = Field(default_factory=list, description="Explicitly blocked categories")

class ApprovalRules(BaseModel):
    amount: float = Field(..., description="Amount above which human approval is required")
    new_merchant: bool = True
    recurring: bool = True
    max_quantity: int = 5

class PolicyDefinition(BaseModel):
    agent_id: str
    version: int = 1
    spending_limits: SpendingLimits
    categories: CategoryPolicy
    allowed_countries: List[str] = Field(default_factory=lambda: ["US", "IN", "GB", "EU", "CA"])
    allowed_currencies: List[str] = Field(default_factory=lambda: ["USD", "EUR", "GBP", "CAD"])
    approval: ApprovalRules
    allowed_merchants: Optional[List[str]] = None  # None means any unless blocked or new
    blocked_merchants: List[str] = Field(default_factory=list)
    allow_subscriptions: bool = False
    max_subscription_period_amount: Optional[float] = None

