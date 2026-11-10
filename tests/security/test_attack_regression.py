import json
import glob
from pathlib import Path
from fastapi.testclient import TestClient

from services.api.main import app
from database.session import SessionLocal
from attack_lab.scenarios import ATTACK_SCENARIOS
from attack_lab.simulator import AttackSimulator

client = TestClient(app)

def test_attack_lab_all_scenarios_neutralized():
    """
    Executes the entire 20-scenario Attack Lab corpus.
    Verifies that every single attack scenario is either BLOCKED or escalated to STEP-UP,
    and that ZERO malicious transactions reach PayPal execution unintercepted.
    """
    db = SessionLocal()
    try:
        # First ensure agent is restored
        client.post("/api/v1/agents/ShoppingAgent-42/restore")

        for scenario in ATTACK_SCENARIOS:
            # Restore before each scenario to isolate the specific vulnerability test
            client.post("/api/v1/agents/ShoppingAgent-42/restore")

            sim_result = AttackSimulator.run_simulation(
                db=db,
                scenario_id=scenario["id"],
                target_agent_id="ShoppingAgent-42"
            )

            # Security Invariant: The attack MUST NOT be unconditionally ALLOWED
            assert sim_result["decision"] in ["BLOCK", "QUARANTINE", "STEP-UP"], (
                f"Attack '{scenario['name']}' was erroneously permitted! Result: {sim_result['decision']}"
            )
            assert sim_result["scores"]["risk_score"] >= 40.0
            assert len(sim_result["reasons"]) > 0
            assert "audit_event_id" in sim_result
    finally:
        db.close()

def test_regression_corpus_files():
    """
    Loads JSON regression fixtures from tests/security/attacks/*.json
    and tests that expected decisions match.
    """
    attack_files = glob.glob(str(Path(__file__).parent / "attacks" / "*.json"))
    assert len(attack_files) >= 6

    for fpath in attack_files:
        with open(fpath, "r", encoding="utf-8") as f:
            corpus = json.load(f)

        # Restore test agent
        client.post("/api/v1/agents/ShoppingAgent-42/restore")

        eval_resp = client.post("/api/v1/security/evaluate", json={
            "agent_id": "ShoppingAgent-42",
            "user_goal": corpus["user_goal"],
            "purpose": corpus["payment_request"].get("purpose", "Item"),
            "amount": corpus["payment_request"]["amount"],
            "currency": corpus["payment_request"].get("currency", "USD"),
            "category": corpus["payment_request"]["category"],
            "quantity": corpus["payment_request"].get("quantity", 1),
            "merchant_id": corpus["payment_request"]["merchant_id"],
            "merchant_name": corpus["payment_request"]["merchant_name"],
            "merchant_country": corpus["payment_request"].get("merchant_country", "US"),
            "expected_merchant_id": corpus["payment_request"].get("expected_merchant_id"),
            "is_recurring": corpus["payment_request"].get("is_recurring", False),
            "nonce": f"nonce_reg_{corpus['test_id']}",
            "timestamp": "2026-11-10T12:00:00",
            "execution_steps": corpus.get("execution_steps", [])
        })

        assert eval_resp.status_code == 200
        res = eval_resp.json()
        assert res["decision"] == corpus["expected_decision"], (
            f"Regression failed for {corpus['test_id']}: expected {corpus['expected_decision']}, got {res['decision']}"
        )

