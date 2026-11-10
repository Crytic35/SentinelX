import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship
from database.session import Base

class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, index=True)
    owner_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    purpose = Column(Text, nullable=True)
    status = Column(String, default="ACTIVE", index=True)  # ACTIVE, SUSPENDED, TERMINATED
    trust_state = Column(String, default="NEW", index=True)
    # NEW -> UNVERIFIED -> TRUSTED -> SUSPICIOUS -> RESTRICTED -> QUARANTINED -> REVOKED
    public_key = Column(Text, nullable=False)
    private_key = Column(Text, nullable=True)  # Stored only for simulated test agents in sandbox
    passport_version = Column(Integer, default=1)
    capabilities = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    passports = relationship("AgentPassport", back_populates="agent", cascade="all, delete-orphan")
    policies = relationship("Policy", back_populates="agent", cascade="all, delete-orphan")
    payment_intents = relationship("PaymentIntent", back_populates="agent", cascade="all, delete-orphan")
    security_events = relationship("SecurityEvent", back_populates="agent", cascade="all, delete-orphan")


class AgentPassport(Base):
    __tablename__ = "agent_passports"

    id = Column(String, primary_key=True, index=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    owner_id = Column(String, nullable=False)
    capabilities = Column(JSON, nullable=False)
    per_transaction_limit = Column(Float, nullable=False)
    daily_limit = Column(Float, nullable=False)
    allowed_categories = Column(JSON, nullable=False)
    blocked_categories = Column(JSON, nullable=False)
    allowed_countries = Column(JSON, nullable=False)
    approval_threshold = Column(Float, nullable=False)
    require_approval_new_merchant = Column(Boolean, default=True)
    require_approval_recurring = Column(Boolean, default=True)
    public_key = Column(Text, nullable=False)
    signature = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    agent = relationship("Agent", back_populates="passports")


class Policy(Base):
    __tablename__ = "policies"

    id = Column(String, primary_key=True, index=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    definition = Column(JSON, nullable=False)
    status = Column(String, default="ACTIVE")  # ACTIVE, ARCHIVED, SUPERSEDED
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    agent = relationship("Agent", back_populates="policies")


class PaymentIntent(Base):
    __tablename__ = "payment_intents"

    id = Column(String, primary_key=True, index=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
    user_goal = Column(Text, nullable=False)
    purpose = Column(String, nullable=False)
    merchant_id = Column(String, nullable=False, index=True)
    merchant_name = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    category = Column(String, nullable=False)
    quantity = Column(Integer, default=1)
    is_recurring = Column(Boolean, default=False)
    recurring_period = Column(String, nullable=True)  # e.g., monthly, annual
    merchant_constraints = Column(JSON, default=list)
    instruction_source = Column(String, default="USER")  # USER, SYSTEM_POLICY, SIGNED_TOOL, KNOWN_API, WEBPAGE, UNTRUSTED_TOOL
    provenance_data = Column(JSON, default=dict)
    signed_payload = Column(JSON, nullable=False)
    nonce = Column(String, nullable=False, index=True)
    signature = Column(Text, nullable=False)
    status = Column(String, default="PENDING", index=True)  # PENDING, EVALUATING, ALLOWED, STEP_UP, RESTRICTED, BLOCKED, QUARANTINED, EXECUTED, FAILED
    decision = Column(String, nullable=True)  # ALLOW, STEP-UP, RESTRICT, BLOCK, QUARANTINE
    approval_status = Column(String, nullable=True)  # PENDING, APPROVED, REJECTED
    approved_by = Column(String, nullable=True)
    approval_scope = Column(String, nullable=True)  # ONCE, MERCHANT_WINDOW, LIMIT_SPECIFIC
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    agent = relationship("Agent", back_populates="payment_intents")
    risk_assessment = relationship("RiskAssessment", back_populates="payment_intent", uselist=False, cascade="all, delete-orphan")
    payment = relationship("Payment", back_populates="payment_intent", uselist=False, cascade="all, delete-orphan")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(String, primary_key=True, index=True)
    payment_intent_id = Column(String, ForeignKey("payment_intents.id"), nullable=False, index=True)
    intent_score = Column(Float, nullable=False)  # 0 to 100
    behavioral_score = Column(Float, nullable=False)  # 0 to 100
    provenance_score = Column(Float, nullable=False)  # 0 to 100
    merchant_score = Column(Float, nullable=False)  # 0 to 100
    overall_risk = Column(String, nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    risk_score = Column(Float, nullable=False)  # 0 to 100 numeric risk index
    decision = Column(String, nullable=False)  # ALLOW, STEP-UP, RESTRICT, BLOCK, QUARANTINE
    policy_result = Column(JSON, default=dict)
    evidence = Column(JSON, default=list)
    reasons = Column(JSON, default=list)
    explanation = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    payment_intent = relationship("PaymentIntent", back_populates="risk_assessment")


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id = Column(String, primary_key=True, index=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True, index=True)
    payment_intent_id = Column(String, nullable=True, index=True)
    event_type = Column(String, nullable=False, index=True)
    severity = Column(String, nullable=False, index=True)  # INFO, LOW, MEDIUM, HIGH, CRITICAL
    summary = Column(Text, nullable=False)
    payload = Column(JSON, default=dict)
    previous_hash = Column(String, nullable=False)
    event_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    agent = relationship("Agent", back_populates="security_events")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, index=True)
    payment_intent_id = Column(String, ForeignKey("payment_intents.id"), nullable=False, index=True)
    paypal_order_id = Column(String, nullable=True, index=True)
    paypal_capture_id = Column(String, nullable=True, index=True)
    status = Column(String, default="CREATED", index=True)  # CREATED, APPROVED, COMPLETED, BLOCKED_PRE_EXECUTION, FAILED
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    trace_id = Column(String, nullable=False, index=True)
    security_receipt = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    payment_intent = relationship("PaymentIntent", back_populates="payment")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True, index=True)
    related_entity = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    actor = Column(String, nullable=False)
    payload = Column(JSON, default=dict)
    previous_hash = Column(String, nullable=False)
    event_hash = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class Tool(Base):
    __tablename__ = "tools"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    owner = Column(String, nullable=False)
    version = Column(String, nullable=False)
    capabilities = Column(JSON, default=list)
    trust_state = Column(String, default="TRUSTED", index=True)  # TRUSTED, UNTRUSTED, HIGH_RISK, REQUIRES_VERIFICATION
    permissions = Column(JSON, default=list)
    last_verification = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    country = Column(String, default="US")
    domain = Column(String, nullable=False)
    category = Column(String, nullable=False)
    trust_score = Column(Float, default=95.0)
    is_verified = Column(Boolean, default=True)
    transaction_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class DelegatedCapability(Base):
    __tablename__ = "delegated_capabilities"

    id = Column(String, primary_key=True, index=True)
    source_agent_id = Column(String, nullable=False, index=True)
    target_agent_id = Column(String, nullable=False, index=True)
    capability = Column(String, nullable=False)
    constraints = Column(JSON, default=dict)
    token = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class GlobalSetting(Base):
    __tablename__ = "global_settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

