from typing import Dict, Any, List, Optional
import uuid

def build_provenance_graph(
    user_goal: str,
    agent_id: str,
    execution_steps: List[Dict[str, Any]],
    payment_request: Dict[str, Any],
    decision: str
) -> Dict[str, Any]:
    """
    Constructs an interactive DAG node-and-edge graph for provenance and decision visualization.
    """
    nodes = []
    edges = []

    # Node 1: User Root
    user_node_id = "node_user"
    nodes.append({
        "id": user_node_id,
        "type": "USER",
        "label": "User Origin",
        "details": f"Original Goal: \"{user_goal}\"",
        "status": "TRUSTED",
        "trust_score": 100
    })

    # Node 2: Agent
    agent_node_id = f"node_agent_{agent_id}"
    nodes.append({
        "id": agent_node_id,
        "type": "AGENT",
        "label": f"AI Agent: {agent_id}",
        "details": "Autonomous execution planner",
        "status": "EVALUATING",
        "trust_score": 90
    })
    edges.append({
        "source": user_node_id,
        "target": agent_node_id,
        "label": "Dispatched User Goal"
    })

    prev_node_id = agent_node_id

    # Add execution/tool step nodes
    for idx, step in enumerate(execution_steps):
        step_id = f"node_step_{idx}"
        source_type = step.get("source_type", "TOOL")
        is_untrusted = source_type in ["WEBPAGE", "UNKNOWN_TOOL", "UNVERIFIED_MCP_TOOL"]
        status = "COMPROMISED" if is_untrusted and step.get("is_malicious", False) else ("UNTRUSTED" if is_untrusted else "TRUSTED")

        nodes.append({
            "id": step_id,
            "type": source_type,
            "label": step.get("name", f"Step {idx+1}"),
            "details": step.get("content", ""),
            "status": status,
            "trust_score": 20 if is_untrusted else 95
        })
        edges.append({
            "source": prev_node_id,
            "target": step_id,
            "label": step.get("action", "invoked")
        })
        prev_node_id = step_id

    # Payment Intent Node
    payment_node_id = "node_payment_intent"
    nodes.append({
        "id": payment_node_id,
        "type": "PAYMENT_INTENT",
        "label": f"Payment Intent: ${payment_request.get('amount', 0):.2f}",
        "details": f"Merchant: {payment_request.get('merchant_name', 'Unknown')} | Item: {payment_request.get('purpose', '')}",
        "status": "SUBMITTED",
        "trust_score": 50
    })
    edges.append({
        "source": prev_node_id,
        "target": payment_node_id,
        "label": "Emitted Payment Request"
    })

    # SentinelX Security Gateway Node
    sentinel_node_id = "node_sentinelx_gateway"
    nodes.append({
        "id": sentinel_node_id,
        "type": "SENTINELX_GATEWAY",
        "label": "SentinelX Zero-Trust Gateway",
        "details": "Deterministic Authorization + AI Context Analysis",
        "status": "DECIDED",
        "trust_score": 100
    })
    edges.append({
        "source": payment_node_id,
        "target": sentinel_node_id,
        "label": "Intercepted Pre-Execution"
    })

    # Final Outcome Node
    outcome_node_id = "node_outcome"
    outcome_status = "SUCCESS" if decision == "ALLOW" else ("STEP_UP" if decision == "STEP-UP" else "BLOCKED")
    nodes.append({
        "id": outcome_node_id,
        "type": "EXECUTION_OUTCOME",
        "label": f"Enforcement: {decision}",
        "details": "PayPal Sandbox Execution" if decision == "ALLOW" else "Blocked Pre-Execution - Never Reached PayPal",
        "status": outcome_status,
        "trust_score": 100 if decision == "ALLOW" else 0
    })
    edges.append({
        "source": sentinel_node_id,
        "target": outcome_node_id,
        "label": f"Decision: {decision}"
    })

    return {
        "nodes": nodes,
        "edges": edges,
        "decision": decision
    }

