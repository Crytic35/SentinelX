from typing import Dict, Any, List

class BlastRadiusCalculator:
    """
    Computes potential financial exposure / blast radius if an agent or collection of agents
    were to be compromised.
    Explains the monetary value protected by SentinelX Zero-Trust controls.
    """

    @staticmethod
    def calculate_agent_blast_radius(
        agent_id: str,
        max_transaction: float,
        daily_limit: float,
        trust_state: str
    ) -> Dict[str, Any]:
        is_quarantined = trust_state in ["QUARANTINED", "REVOKED"]
        effective_max = 0.0 if is_quarantined else max_transaction
        effective_daily = 0.0 if is_quarantined else daily_limit

        return {
            "agent_id": agent_id,
            "trust_state": trust_state,
            "per_transaction_exposure": effective_max,
            "daily_24h_exposure": effective_daily,
            "weekly_exposure": effective_daily * 7.0,
            "is_mitigated": is_quarantined,
            "mitigation_notes": "Execution fully blocked by quarantine" if is_quarantined else "Active exposure within passport limits"
        }

    @staticmethod
    def calculate_fleet_blast_radius(agents: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_per_tx = 0.0
        total_daily = 0.0
        total_protected = 0.0
        active_agents = 0

        for a in agents:
            state = a.get("trust_state", "TRUSTED")
            max_tx = float(a.get("per_transaction_limit", 500.0))
            daily = float(a.get("daily_limit", 1500.0))

            if state in ["QUARANTINED", "REVOKED"]:
                total_protected += daily
            else:
                total_per_tx += max_tx
                total_daily += daily
                active_agents += 1

        return {
            "total_active_agents": active_agents,
            "total_per_transaction_exposure": total_per_tx,
            "total_daily_exposure": total_daily,
            "total_quarantined_mitigated_exposure": total_protected,
            "exposure_currency": "USD"
        }

