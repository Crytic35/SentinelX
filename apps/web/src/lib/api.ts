const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

export async function fetchMetrics() {
  const res = await fetch(`${API_BASE}/security/metrics`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch metrics");
  return res.json();
}

export async function fetchAgents() {
  const res = await fetch(`${API_BASE}/agents`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch agents");
  return res.json();
}

export async function fetchAgentDetails(agentId: string) {
  const res = await fetch(`${API_BASE}/agents/${agentId}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch agent details");
  return res.json();
}

export async function fetchAgentScorecard(agentId: string) {
  const res = await fetch(`${API_BASE}/agents/${agentId}/scorecard`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch agent scorecard");
  return res.json();
}

export async function fetchSecurityEvents(limit: number = 30) {
  const res = await fetch(`${API_BASE}/security/events?limit=${limit}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch security events");
  return res.json();
}

export async function verifyAuditChain() {
  const res = await fetch(`${API_BASE}/security/verify-audit-chain`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to verify audit chain");
  return res.json();
}

export async function fetchAttackScenarios() {
  const res = await fetch(`${API_BASE}/attack-lab/scenarios`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch scenarios");
  return res.json();
}

export async function simulateAttack(scenarioId: string, customPayload?: any, targetAgentId: string = "ShoppingAgent-42") {
  const res = await fetch(`${API_BASE}/attack-lab/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      scenario_id: scenarioId,
      custom_payload: customPayload,
      target_agent_id: targetAgentId,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Simulation failed" }));
    throw new Error(err.detail || "Simulation failed");
  }
  return res.json();
}

export async function runRedTeamSuite(targetAgentId: string = "ShoppingAgent-42") {
  const res = await fetch(`${API_BASE}/attack-lab/red-team/run?target_agent_id=${targetAgentId}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to execute Red-Team suite");
  return res.json();
}

export async function evaluatePayment(payload: any) {
  const res = await fetch(`${API_BASE}/security/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Evaluation failed" }));
    throw new Error(err.detail || "Evaluation failed");
  }
  return res.json();
}

export async function executePayPalOrder(paymentIntentId: string) {
  const res = await fetch(`${API_BASE}/payments/paypal/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ payment_intent_id: paymentIntentId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "PayPal order creation failed" }));
    throw new Error(err.detail || "PayPal order creation failed");
  }
  return res.json();
}

export async function capturePayPalOrder(paymentIntentId: string, paypalOrderId: string) {
  const res = await fetch(`${API_BASE}/payments/paypal/capture`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ payment_intent_id: paymentIntentId, paypal_order_id: paypalOrderId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "PayPal capture failed" }));
    throw new Error(err.detail || "PayPal capture failed");
  }
  return res.json();
}

export async function handleHumanApproval(paymentIntentId: string, action: string, scope: string = "ONCE", notes?: string) {
  const res = await fetch(`${API_BASE}/security/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      payment_intent_id: paymentIntentId,
      action: action,
      approved_by: "SecOps Lead",
      scope: scope,
      notes: notes,
    }),
  });
  if (!res.ok) throw new Error("Approval submission failed");
  return res.json();
}

export async function quarantineAgent(agentId: string, reason: string = "Manual console quarantine") {
  const res = await fetch(`${API_BASE}/agents/${agentId}/quarantine?reason=${encodeURIComponent(reason)}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Quarantine failed");
  return res.json();
}

export async function restoreAgent(agentId: string) {
  const res = await fetch(`${API_BASE}/agents/${agentId}/restore`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Restore failed");
  return res.json();
}

export async function toggleGlobalFreeze(enable: boolean) {
  const res = await fetch(`${API_BASE}/security/freeze?enable=${enable}&authorized_by=SecOps%20Lead`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Freeze toggle failed");
  return res.json();
}

export async function querySecurityAnalyst(query: string, agentId: string = "ShoppingAgent-42") {
  const res = await fetch(`${API_BASE}/analyst/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, agent_id: agentId }),
  });
  if (!res.ok) throw new Error("Analyst query failed");
  return res.json();
}

export async function convertNaturalLanguagePolicy(prompt: string, agentId: string = "ShoppingAgent-42") {
  const res = await fetch(`${API_BASE}/policies/natural-language`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, agent_id: agentId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Parse error" }));
    throw new Error(err.detail || "Parse error");
  }
  return res.json();
}

export async function simulatePolicy(agentId: string, proposedPolicy: any) {
  const res = await fetch(`${API_BASE}/policies/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agent_id: agentId, proposed_policy: proposedPolicy }),
  });
  if (!res.ok) throw new Error("Policy simulation failed");
  return res.json();
}

export async function fetchMerchants() {
  const res = await fetch(`${API_BASE}/merchants`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch merchants");
  return res.json();
}

export async function fetchTools() {
  const res = await fetch(`${API_BASE}/tools`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch tools");
  return res.json();
}

export async function fetchPaymentHistory() {
  const res = await fetch(`${API_BASE}/payments/history`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch payment history");
  return res.json();
}

