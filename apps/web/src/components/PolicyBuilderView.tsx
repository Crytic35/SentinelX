"use client";

import React, { useState } from "react";
import { Sliders, Sparkles, CheckCircle2, AlertTriangle, Code, Play } from "lucide-react";
import { convertNaturalLanguagePolicy, simulatePolicy } from "@/lib/api";

export function PolicyBuilderView() {
  const [nlPrompt, setNlPrompt] = useState(
    "Allow my shopping agent to spend up to $500 on electronics and books, but require approval above $300."
  );
  const [parsing, setParsing] = useState(false);
  const [parsedPolicy, setParsedPolicy] = useState<any>(null);
  const [simulating, setSimulating] = useState(false);
  const [simulationResult, setSimulationResult] = useState<any>(null);

  const sampleYAML = `agent: ShoppingAgent-42
version: 1
spending_limits:
  max_transaction: 500.00
  daily_limit: 1500.00
categories:
  allow:
    - electronics
    - books
  deny:
    - cryptocurrency
    - gift_cards
approval:
  amount: 300.00
  new_merchant: true
  recurring: true`;

  const handleParseNL = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setParsing(true);
      const res = await convertNaturalLanguagePolicy(nlPrompt, "ShoppingAgent-42");
      setParsedPolicy(res.proposed_policy);
    } catch (err: any) {
      alert("Policy parse error: " + err.message);
    } finally {
      setParsing(false);
    }
  };

  const handleSimulateHypothetical = async () => {
    const policyToSim = parsedPolicy || {
      spending_limits: { max_transaction: 100.0, daily_limit: 500.0 },
      categories: { allow: ["electronics"], deny: ["cryptocurrency"] },
      approval: { amount: 80.0, new_merchant: true, recurring: true }
    };

    try {
      setSimulating(true);
      const sim = await simulatePolicy("ShoppingAgent-42", policyToSim);
      setSimulationResult(sim);
    } catch (err: any) {
      alert("Simulation error: " + err.message);
    } finally {
      setSimulating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-surface-border pb-4">
        <div>
          <h2 className="text-xl font-bold text-white font-mono flex items-center gap-2">
            <Sliders className="w-6 h-6 text-brand-cyan" />
            POLICY ENGINE &amp; NATURAL-LANGUAGE POLICY BUILDER
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic Policy-as-Code. Speak in plain English — AI drafts structured schema rules with automated conflict checking.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Natural-Language Policy Creator */}
        <div className="bg-surface border border-surface-border rounded-xl p-5 space-y-4">
          <h3 className="text-sm font-bold text-white font-mono flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            NATURAL-LANGUAGE POLICY DRAFTER
          </h3>
          <p className="text-xs text-slate-400">
            Describe rules in conversational English. SentinelX strictly verifies schema invariants and checks for rule conflicts before proposing.
          </p>

          <form onSubmit={handleParseNL} className="space-y-3 font-mono text-xs">
            <textarea
              rows={3}
              value={nlPrompt}
              onChange={(e) => setNlPrompt(e.target.value)}
              className="w-full bg-surface-raised border border-surface-border rounded-lg p-3 text-white focus:outline-none focus:border-cyan-400 resize-none"
              placeholder="e.g., Allow spending up to $200 on books, deny crypto..."
            />

            <button
              type="submit"
              disabled={parsing}
              className="w-full py-2.5 rounded-lg bg-gradient-to-r from-brand-blue to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white font-bold transition flex items-center justify-center gap-2"
            >
              <Sparkles className="w-4 h-4" />
              <span>{parsing ? "Analyzing & Validating..." : "Draft Structured Policy"}</span>
            </button>
          </form>

          {parsedPolicy && (
            <div className="p-3.5 rounded-lg bg-surface-raised border border-cyan-800/60 font-mono text-xs space-y-2">
              <div className="flex items-center justify-between text-cyan-300 font-bold">
                <span>✓ Schema &amp; Conflict Checks Passed</span>
                <span className="text-[10px] bg-cyan-950 px-2 py-0.5 rounded border border-cyan-800">Ready</span>
              </div>
              <div className="bg-[#080b11] p-3 rounded text-[11px] text-slate-200 overflow-x-auto">
                <pre>{JSON.stringify(parsedPolicy, null, 2)}</pre>
              </div>
              <button
                onClick={handleSimulateHypothetical}
                disabled={simulating}
                className="w-full mt-2 py-2 rounded bg-surface border border-surface-border hover:bg-surface-border text-cyan-300 font-semibold transition"
              >
                {simulating ? "Replaying History..." : "Simulate Against Historical Transactions"}
              </button>
            </div>
          )}
        </div>

        {/* Right: Active Policy-as-Code & Simulator */}
        <div className="bg-surface border border-surface-border rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-surface-border pb-3">
            <h3 className="text-sm font-bold text-white font-mono flex items-center gap-2">
              <Code className="w-4 h-4 text-emerald-400" />
              POLICY-AS-CODE (IMMUTABLE v1)
            </h3>
            <span className="text-xs font-mono text-emerald-400 bg-emerald-950/40 border border-emerald-800/40 px-2 py-0.5 rounded">
              Active Enforcement
            </span>
          </div>

          <div className="bg-[#080b11] p-3 rounded-lg border border-surface-border font-mono text-xs text-emerald-300 overflow-x-auto">
            <pre>{sampleYAML}</pre>
          </div>

          {/* Historical Simulation Output */}
          {simulationResult && (
            <div className="p-3 rounded-lg bg-amber-950/30 border border-amber-800 font-mono text-xs space-y-2">
              <span className="font-bold text-amber-300 block">POLICY REPLAY SIMULATION RESULTS</span>
              <div className="grid grid-cols-3 gap-2 text-[11px]">
                <div>
                  <span className="text-slate-400 block">REPLAYED TXs</span>
                  <span className="text-white font-bold">{simulationResult.historical_transactions_analyzed}</span>
                </div>
                <div>
                  <span className="text-slate-400 block">NEWLY BLOCKED</span>
                  <span className="text-red-400 font-bold">{simulationResult.newly_blocked_count}</span>
                </div>
                <div>
                  <span className="text-slate-400 block">LEGIT IMPACTED</span>
                  <span className="text-amber-400 font-bold">{simulationResult.legitimate_transactions_impacted}</span>
                </div>
              </div>
              {simulationResult.over_restriction_warning && (
                <p className="text-[10px] text-amber-200 bg-amber-900/40 p-2 rounded">
                  ⚠️ Over-restriction Warning: Proposed policy would have blocked previously approved legitimate transactions.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

