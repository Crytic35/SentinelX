from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.session import get_db
from attack_lab.scenarios import ATTACK_SCENARIOS
from attack_lab.simulator import AttackSimulator
from attack_lab.red_team import RedTeamSuite

router = APIRouter(prefix="/attack-lab", tags=["Attack Lab & Simulation"])

class SimulateAttackRequest(BaseModel):
    scenario_id: str
    custom_payload: Optional[Dict[str, Any]] = None
    target_agent_id: str = "ShoppingAgent-42"

@router.get("/scenarios")
def list_attack_scenarios():
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "category": s["category"],
            "severity": s["severity"],
            "description": s["description"],
            "user_goal": s["user_goal"],
            "requested_amount": s["agent_request"]["amount"],
            "category_target": s["agent_request"]["category"],
            "expected_defense": s["expected_defense"]
        } for s in ATTACK_SCENARIOS
    ]

@router.post("/simulate")
def simulate_attack(req: SimulateAttackRequest, db: Session = Depends(get_db)):
    try:
        result = AttackSimulator.run_simulation(
            db=db,
            scenario_id=req.scenario_id,
            custom_payload=req.custom_payload,
            target_agent_id=req.target_agent_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")

@router.post("/replay")
def replay_attack(req: SimulateAttackRequest, db: Session = Depends(get_db)):
    # Replay runs the simulation again and produces the sequential timeline
    return simulate_attack(req, db)

@router.post("/red-team/run")
def run_red_team_suite(target_agent_id: str = "ShoppingAgent-42", db: Session = Depends(get_db)):
    suite_metrics = RedTeamSuite.run_full_suite(db=db, target_agent_id=target_agent_id)
    return suite_metrics

