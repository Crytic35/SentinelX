import pytest
import uuid
from datetime import datetime
from security.identity.crypto import generate_agent_keypair, sign_payload, verify_signature, hash_content
from security.identity.passport import AgentPassportModel, TrustState
from security.policies.schema import PolicyDefinition, SpendingLimits, CategoryPolicy, ApprovalRules
from security.policies.engine import PolicyEngine
from security.replay.nonce_store import NonceStore
from security.merchant.registry import MerchantSecurityService
from agents.intent.analyzer import IntentAnalyzer
from agents.intent.drift_detector import IntentDriftDetector
from agents.behavior.baseline import BehaviorAnalyzer, AgentBehavioralFingerprint
from security.audit.tamper_evident_log import compute_event_hash, GENESIS_HASH

def test_cryptographic_keypair_and_signatures():
    pub_hex, priv_hex = generate_agent_keypair()
    assert len(pub_hex) == 64
    assert len(priv_hex) == 64

    payload = {"agent_id": "Agent-007", "amount": 149.99, "currency": "USD"}
    signature = sign_payload(payload, priv_hex)
    assert len(signature) == 128

    # Positive verification
    assert verify_signature(payload, signature, pub_hex) is True

    # Negative verification: tampered payload
    tampered_payload = {"agent_id": "Agent-007", "amount": 9999.99, "currency": "USD"}
    assert verify_signature(tampered_payload, signature, pub_hex) is False

def test_agent_passport_signature_and_verification():
    pub_hex, priv_hex = generate_agent_keypair()
    passport = AgentPassportModel(
        agent_id="ShoppingAgent-Test",
        owner_id="Alice",
        version=1,
        capabilities=["search_products", "cart_management", "initiate_merchant_payments"],
        per_transaction_limit=500.0,
        daily_limit=1500.0,
        allowed_categories=["electronics", "books"],
        blocked_categories=["cryptocurrency", "gift cards"],
        allowed_countries=["US", "IN"],
        approval_threshold=300.0,
        public_key=pub_hex
    )
    passport.sign(priv_hex)
    assert passport.signature is not None
    assert passport.verify() is True

def test_deterministic_policy_spending_limits():
    policy = PolicyDefinition(
        agent_id="Agent-42",
        version=1,
        spending_limits=SpendingLimits(max_transaction=500.0, daily_limit=1500.0),
        categories=CategoryPolicy(allow=["electronics", "books"], deny=["cryptocurrency", "gift cards"]),
        allowed_countries=["US", "IN"],
        allowed_currencies=["USD"],
        approval=ApprovalRules(amount=300.0, new_merchant=True, recurring=True, max_quantity=5)
    )

    # Allowed transaction below limit
    res_ok = PolicyEngine.evaluate(
        policy=policy,
        amount=120.0,
        currency="USD",
        category="electronics",
        merchant_id="merch_bestbuy_01",
        merchant_country="US",
        is_new_merchant=False,
        quantity=1,
        is_recurring=False
    )
    assert res_ok.allowed is True
    assert res_ok.decision == "ALLOW"

    # Blocked: exceeds per-transaction limit
    res_exceed = PolicyEngine.evaluate(
        policy=policy,
        amount=1200.0,
        currency="USD",
        category="electronics",
        merchant_id="merch_bestbuy_01",
        merchant_country="US",
        is_new_merchant=False,
        quantity=1,
        is_recurring=False
    )
    assert res_exceed.allowed is False
    assert res_exceed.decision == "BLOCK"
    assert any("max_transaction_limit" in v["rule"] for v in res_exceed.violations)

    # Blocked: cumulative daily spend breach
    res_daily = PolicyEngine.evaluate(
        policy=policy,
        amount=400.0,
        currency="USD",
        category="electronics",
        merchant_id="merch_bestbuy_01",
        merchant_country="US",
        is_new_merchant=False,
        quantity=1,
        is_recurring=False,
        current_daily_spend=1300.0
    )
    assert res_daily.allowed is False
    assert res_daily.decision == "BLOCK"
    assert any("daily_spending_limit" in v["rule"] for v in res_daily.violations)

def test_category_allow_and_deny_enforcement():
    policy = PolicyDefinition(
        agent_id="Agent-42",
        spending_limits=SpendingLimits(max_transaction=500.0, daily_limit=1500.0),
        categories=CategoryPolicy(allow=["electronics", "books"], deny=["cryptocurrency", "gift cards"]),
        approval=ApprovalRules(amount=300.0)
    )

    # Forbidden category: crypto
    res_crypto = PolicyEngine.evaluate(
        policy=policy,
        amount=50.0,
        currency="USD",
        category="cryptocurrency",
        merchant_id="merch_bestbuy_01",
        merchant_country="US",
        is_new_merchant=False,
        quantity=1,
        is_recurring=False
    )
    assert res_crypto.allowed is False
    assert any("blocked_category" in v["rule"] for v in res_crypto.violations)

    # Disallowed category not in allowlist
    res_apparel = PolicyEngine.evaluate(
        policy=policy,
        amount=50.0,
        currency="USD",
        category="apparel",
        merchant_id="merch_bestbuy_01",
        merchant_country="US",
        is_new_merchant=False,
        quantity=1,
        is_recurring=False
    )
    assert res_apparel.allowed is False
    assert any("allowed_categories" in v["rule"] for v in res_apparel.violations)

def test_approval_threshold_step_up():
    policy = PolicyDefinition(
        agent_id="Agent-42",
        spending_limits=SpendingLimits(max_transaction=500.0, daily_limit=1500.0),
        categories=CategoryPolicy(allow=["electronics"]),
        approval=ApprovalRules(amount=300.0, new_merchant=True, recurring=True)
    )

    # $350 is within $500 max limit, but > $300 approval threshold -> triggers STEP-UP
    res = PolicyEngine.evaluate(
        policy=policy,
        amount=350.0,
        currency="USD",
        category="electronics",
        merchant_id="merch_bestbuy_01",
        merchant_country="US",
        is_new_merchant=False,
        quantity=1,
        is_recurring=False
    )
    assert res.allowed is True
    assert res.requires_step_up is True
    assert res.decision == "STEP-UP"

def test_replay_protection_and_nonce_uniqueness():
    store = NonceStore()
    now_iso = datetime.utcnow().isoformat()
    test_nonce = f"test_nonce_{uuid.uuid4().hex}"

    # First attempt succeeds
    ok1, msg1 = store.validate_and_record_nonce(test_nonce, now_iso)
    assert ok1 is True

    # Replay attempt with same nonce MUST be rejected
    ok2, msg2 = store.validate_and_record_nonce(test_nonce, now_iso)
    assert ok2 is False
    assert "Replay attack detected" in msg2

def test_intent_drift_detection():
    expected = IntentAnalyzer.extract_expected_intent("Buy an SSD under $150")
    assert expected.max_amount == 150.0
    assert expected.category == "electronics"

    # Drastic drift: 10 GPUs for $4,800
    actual = {
        "amount": 4800.0,
        "category": "electronics",
        "quantity": 10,
        "purpose": "10x Nvidia RTX 4090 GPUs"
    }
    report = IntentDriftDetector.detect_drift(expected, actual)
    assert report.drift_detected is True
    assert len(report.deviations) >= 2  # amount + quantity deviations
    assert report.semantic_similarity_score < 50.0

def test_behavior_baseline_anomaly():
    fp = AgentBehavioralFingerprint(agent_id="ShoppingAgent-42", median_amount=96.0, p95_amount=250.0)
    
    # Normal transaction: $89
    normal = BehaviorAnalyzer.evaluate_behavior(fp, 89.0, "electronics", "merch_bestbuy_01")
    assert normal["status"] == "NORMAL"
    assert normal["behavior_score"] > 80.0

    # Anomalous transaction: $3,800
    anom = BehaviorAnalyzer.evaluate_behavior(fp, 3800.0, "electronics", "merch_bestbuy_01")
    assert anom["status"] == "EXTREME_ANOMALY"
    assert anom["behavior_score"] < 40.0

def test_merchant_destination_binding():
    # Correct destination
    valid, is_new, score, anoms = MerchantSecurityService.verify_merchant(
        merchant_id="merch_bestbuy_01",
        merchant_name="Best Buy Official",
        category="electronics",
        expected_merchant_id="merch_bestbuy_01"
    )
    assert valid is True
    assert len([a for a in anoms if a.get("severity") == "CRITICAL"]) == 0

    # Substituted destination
    valid_sub, is_new, score, anoms_sub = MerchantSecurityService.verify_merchant(
        merchant_id="merch_attacker_998",
        merchant_name="Attacker Shell",
        category="electronics",
        expected_merchant_id="merch_bestbuy_01"
    )
    assert valid_sub is False
    assert any("destination_substitution" in a.get("signal", "") for a in anoms_sub)

def test_tamper_evident_audit_hash_chaining():
    payload_1 = {"event": "FIRST_EVENT", "amount": 100}
    hash_1 = compute_event_hash(payload_1, GENESIS_HASH)
    assert len(hash_1) == 64

    payload_2 = {"event": "SECOND_EVENT", "amount": 200}
    hash_2 = compute_event_hash(payload_2, hash_1)
    assert len(hash_2) == 64
    assert hash_2 != hash_1

    # Tampering payload_1 alters its hash, which invalidates hash_2's dependency
    tampered_payload_1 = {"event": "FIRST_EVENT", "amount": 99999}
    tampered_hash_1 = compute_event_hash(tampered_payload_1, GENESIS_HASH)
    assert tampered_hash_1 != hash_1

