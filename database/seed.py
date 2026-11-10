import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database.session import SessionLocal, engine, Base
from database.models import Agent, AgentPassport, Policy, Tool, Merchant, PaymentIntent, RiskAssessment, Payment, SecurityEvent
from security.identity.crypto import generate_agent_keypair
from security.identity.passport import AgentPassportModel, TrustState
from security.audit.tamper_evident_log import record_security_event, GENESIS_HASH
from paypal.payment.receipt import SecurityReceipt

def seed_database(db: Session):
    # Create tables if not exist
    Base.metadata.create_all(bind=engine)

    # Check if already seeded
    if db.query(Agent).filter(Agent.id == "ShoppingAgent-42").first():
        return

    # 1. Generate Ed25519 Keys for ShoppingAgent-42
    pub_key_hex, priv_key_hex = generate_agent_keypair()

    # 2. Create ShoppingAgent-42
    agent = Agent(
        id="ShoppingAgent-42",
        owner_id="Alice",
        name="ShoppingAgent-42",
        purpose="Autonomous shopping and price comparison agent for office hardware and tech literature",
        status="ACTIVE",
        trust_state=TrustState.TRUSTED,
        public_key=pub_key_hex,
        private_key=priv_key_hex,
        passport_version=1,
        capabilities=["search_products", "cart_management", "initiate_merchant_payments", "view_orders"],
        created_at=datetime.utcnow() - timedelta(days=14)
    )
    db.add(agent)
    db.flush()

    # 3. Create Agent Passport v1
    passport_model = AgentPassportModel(
        passport_id="psp_shopping_42_v1",
        agent_id="ShoppingAgent-42",
        owner_id="Alice",
        version=1,
        capabilities=["search_products", "cart_management", "initiate_merchant_payments", "view_orders"],
        per_transaction_limit=500.0,
        daily_limit=1500.0,
        allowed_categories=["electronics", "books"],
        blocked_categories=["cryptocurrency", "gift cards", "weapons", "gambling"],
        allowed_countries=["US", "IN", "GB", "EU", "CA"],
        approval_threshold=300.0,
        require_approval_new_merchant=True,
        require_approval_recurring=True,
        public_key=pub_key_hex
    )
    passport_model.sign(priv_key_hex)

    db_passport = AgentPassport(
        id=passport_model.passport_id,
        agent_id=agent.id,
        version=passport_model.version,
        owner_id=passport_model.owner_id,
        capabilities=passport_model.capabilities,
        per_transaction_limit=passport_model.per_transaction_limit,
        daily_limit=passport_model.daily_limit,
        allowed_categories=passport_model.allowed_categories,
        blocked_categories=passport_model.blocked_categories,
        allowed_countries=passport_model.allowed_countries,
        approval_threshold=passport_model.approval_threshold,
        require_approval_new_merchant=passport_model.require_approval_new_merchant,
        require_approval_recurring=passport_model.require_approval_recurring,
        public_key=passport_model.public_key,
        signature=passport_model.signature,
        created_at=datetime.utcnow() - timedelta(days=14)
    )
    db.add(db_passport)

    # 4. Create Active Policy
    policy_def = {
        "spending_limits": {"max_transaction": 500.0, "daily_limit": 1500.0},
        "categories": {"allow": ["electronics", "books"], "deny": ["cryptocurrency", "gift cards"]},
        "allowed_countries": ["US", "IN", "GB", "EU", "CA"],
        "allowed_currencies": ["USD", "EUR", "GBP"],
        "approval": {"amount": 300.0, "new_merchant": True, "recurring": True, "max_quantity": 5}
    }
    policy = Policy(
        id="pol_shopping_42_v1",
        agent_id=agent.id,
        version=1,
        definition=policy_def,
        status="ACTIVE",
        is_active=True,
        created_at=datetime.utcnow() - timedelta(days=14)
    )
    db.add(policy)

    # 5. Seed Trusted Tools
    tools = [
        Tool(
            id="tool_product_search",
            name="ProductCatalogSearch",
            owner="RetailHub",
            version="2.1.0",
            capabilities=["search_products"],
            trust_state="TRUSTED",
            permissions=["read:catalog"]
        ),
        Tool(
            id="tool_cart_manager",
            name="SecureCartManager",
            owner="SentinelX Core",
            version="1.0.4",
            capabilities=["cart_management"],
            trust_state="TRUSTED",
            permissions=["write:cart"]
        ),
        Tool(
            id="tool_web_scraper",
            name="GenericWebScraper",
            owner="ThirdPartyCommunity",
            version="0.8.2",
            capabilities=["scrape_html"],
            trust_state="UNTRUSTED",
            permissions=["net:fetch"]
        ),
        Tool(
            id="tool_mcp_unverified",
            name="ExternalMCPExtension",
            owner="UnknownDev",
            version="0.1.0",
            capabilities=["unrestricted_eval"],
            trust_state="REQUIRES_VERIFICATION",
            permissions=["system:all"]
        )
    ]
    for t in tools:
        db.add(t)

    # 6. Seed Merchants
    merchants = [
        Merchant(
            id="merch_bestbuy_01",
            name="Best Buy Official",
            domain="bestbuy.com",
            country="US",
            category="electronics",
            trust_score=98.0,
            is_verified=True,
            transaction_count=18
        ),
        Merchant(
            id="merch_newegg_02",
            name="Newegg Electronics",
            domain="newegg.com",
            country="US",
            category="electronics",
            trust_score=96.0,
            is_verified=True,
            transaction_count=12
        ),
        Merchant(
            id="merch_barnesnoble_03",
            name="Barnes & Noble",
            domain="barnesandnoble.com",
            country="US",
            category="books",
            trust_score=99.0,
            is_verified=True,
            transaction_count=7
        )
    ]
    for m in merchants:
        db.add(m)

    # 7. Seed Legitimate Historical Transactions
    historical_txs = [
        {"amt": 49.0, "purpose": "Computer Architecture Handbook", "category": "books", "merch": "merch_barnesnoble_03", "merch_name": "Barnes & Noble", "days_ago": 6},
        {"amt": 129.0, "purpose": "Samsung 980 Pro NVMe SSD 1TB", "category": "electronics", "merch": "merch_bestbuy_01", "merch_name": "Best Buy Official", "days_ago": 4},
        {"amt": 89.0, "purpose": "Mechanical Ergonomic Keyboard", "category": "electronics", "merch": "merch_newegg_02", "merch_name": "Newegg Electronics", "days_ago": 2},
        {"amt": 199.0, "purpose": "Dell 27-inch 4K Monitor", "category": "electronics", "merch": "merch_bestbuy_01", "merch_name": "Best Buy Official", "days_ago": 1}
    ]

    for tx in historical_txs:
        pi_id = f"pi_hist_{uuid.uuid4().hex[:10]}"
        pi = PaymentIntent(
            id=pi_id,
            agent_id=agent.id,
            user_goal=f"Buy {tx['purpose']} under ${tx['amt'] * 1.2:.0f}",
            purpose=tx["purpose"],
            merchant_id=tx["merch"],
            merchant_name=tx["merch_name"],
            amount=tx["amt"],
            currency="USD",
            category=tx["category"],
            quantity=1,
            is_recurring=False,
            instruction_source="USER",
            signed_payload={"amount": tx["amt"], "purpose": tx["purpose"]},
            nonce=f"nonce_hist_{uuid.uuid4().hex[:8]}",
            signature="sig_valid_seed_hex",
            status="EXECUTED",
            decision="ALLOW",
            approval_status="APPROVED",
            created_at=datetime.utcnow() - timedelta(days=tx["days_ago"]),
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        db.add(pi)
        db.flush()

        ra = RiskAssessment(
            id=f"ra_{uuid.uuid4().hex[:10]}",
            payment_intent_id=pi.id,
            intent_score=98.0,
            behavioral_score=96.0,
            provenance_score=100.0,
            merchant_score=98.0,
            overall_risk="LOW",
            risk_score=8.5,
            decision="ALLOW",
            policy_result={"allowed": True},
            evidence=[{"signal": "policy_check", "status": "PASS"}],
            reasons=["Transaction strictly within limits and historical profile"],
            explanation=f"Transaction of ${tx['amt']:.2f} to {tx['merch_name']} was verified and authorized.",
            created_at=datetime.utcnow() - timedelta(days=tx["days_ago"])
        )
        db.add(ra)

        # PayPal Sandbox order record
        paypal_id = f"PAYPAL-SANDBOX-{uuid.uuid4().hex[:10].upper()}"
        receipt = SecurityReceipt.generate_receipt(
            paypal_order_id=paypal_id,
            decision_id=ra.id,
            agent_id=agent.id,
            passport_version=1,
            policy_version=1,
            intent_id=pi.id,
            risk_assessment_id=ra.id,
            security_event_id="sec_seed_initial",
            amount=tx["amt"],
            currency="USD",
            decision="ALLOW",
            risk_level="LOW",
            risk_score=8.5,
            checks_passed=["identity", "passport", "policy", "behavior", "provenance"]
        )

        payment = Payment(
            id=f"pay_{uuid.uuid4().hex[:10]}",
            payment_intent_id=pi.id,
            paypal_order_id=paypal_id,
            paypal_capture_id=f"CAP-{uuid.uuid4().hex[:8].upper()}",
            status="COMPLETED",
            amount=tx["amt"],
            currency="USD",
            trace_id=f"trace_{uuid.uuid4().hex[:12]}",
            security_receipt=receipt,
            created_at=datetime.utcnow() - timedelta(days=tx["days_ago"])
        )
        db.add(payment)

    db.commit()

    # Record initial seed security event
    record_security_event(
        db=db,
        agent_id=agent.id,
        payment_intent_id=None,
        event_type="AGENT_INITIALIZED",
        severity="INFO",
        summary="Agent ShoppingAgent-42 initialized with Ed25519 identity and Passport v1",
        payload={
            "agent_id": agent.id,
            "owner": agent.owner_id,
            "limits": {"max_transaction": 500.0, "daily_limit": 1500.0}
        }
    )

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_database(db)
        print("Database successfully seeded.")
    finally:
        db.close()

