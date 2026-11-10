"use client";

import React, { useState } from "react";
import {
  ShieldCheck,
  ShieldAlert,
  AlertOctagon,
  DollarSign,
  Activity,
  Zap,
  ArrowUpRight,
  Lock,
  Unlock,
  CheckCircle2,
  XCircle,
  Clock,
  Send,
  Play
} from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import { quarantineAgent, restoreAgent, evaluatePayment, executePayPalOrder, capturePayPalOrder } from "@/lib/api";

interface DashboardViewProps {
  metrics: any;
  agents: any[];
  recentEvents: any[];
  onRefresh: () => void;
  onNavigateTab: (tab: string) => void;
}

export function DashboardView({ metrics, agents, recentEvents, onRefresh, onNavigateTab }: DashboardViewProps) {
  const primaryAgent = agents.find((a) => a.id === "ShoppingAgent-42") || agents[0];
  const [acting, setActing] = useState(false);
  const [liveAmount, setLiveAmount] = useState("129.00");
  const [liveGoal, setLiveGoal] = useState("Buy 1TB NVMe SSD under $150");
  const [liveCategory, setLiveCategory] = useState("electronics");
  const [liveResult, setLiveResult] = useState<any>(null);
  const [executingPayPal, setExecutingPayPal] = useState(false);

  const handleQuarantine = async (agentId: string) => {
    try {
      setActing(true);
      await quarantineAgent(agentId, "Operator dashboard emergency containment");
      onRefresh();
    } catch (err) {
      alert("Quarantine error: " + err);
    } finally {
      setActing(false);
    }
  };

  const handleRestore = async (agentId: string) => {
    try {
      setActing(true);
      await restoreAgent(agentId);
      onRefresh();
    } catch (err) {
      alert("Restore error: " + err);
    } finally {
      setActing(false);
    }
  };

  const handleLivePaymentTest = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setExecutingPayPal(true);
      setLiveResult(null);

      const amt = parseFloat(liveAmount);
      const evalResp = await evaluatePayment({
        agent_id: primaryAgent?.id || "ShoppingAgent-42",
        user_goal: liveGoal,
        purpose: liveGoal,
        amount: amt,
        currency: "USD",
        category: liveCategory,
        quantity: 1,
        merchant_id: "merch_bestbuy_01",
        merchant_name: "Best Buy Official",
        merchant_country: "US",
        nonce: `console_${Date.now()}`,
        timestamp: new Date().toISOString(),
        execution_steps: [
          { name: "Console Trigger", source_type: "USER", content: liveGoal }
        ]
      });

      setLiveResult(evalResp);

      // If ALLOWED, trigger PayPal sandbox creation & capture
      if (evalResp.can_proceed_to_paypal) {
        const orderResp = await executePayPalOrder(evalResp.payment_intent_id);
        const captureResp = await capturePayPalOrder(evalResp.payment_intent_id, orderResp.paypal_order_id);
        setLiveResult({
          ...evalResp,
          paypal_order: orderResp.paypal_order,
          security_receipt: captureResp.security_receipt
        });
      }

      onRefresh();
    } catch (err: any) {
      alert("Payment test error: " + err.message);
    } finally {
      setExecutingPayPal(false);
    }
  };

  const trustColor =
    primaryAgent?.trust_state === "TRUSTED"
      ? "text-emerald-400 bg-emerald-950/40 border-emerald-800/40"
      : primaryAgent?.trust_state === "RESTRICTED"
      ? "text-amber-400 bg-amber-950/40 border-amber-800/40"
      : "text-red-400 bg-red-950/40 border-red-800/40";

  return (
    <div className="space-y-6">
      {/* Top Banner Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1 */}
        <div className="bg-surface border border-surface-border rounded-xl p-4 relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
            <span>PROTECTED FLEET</span>
            <ShieldCheck className="w-4 h-4 text-brand-cyan" />
          </div>
          <div className="mt-2 text-2xl font-bold text-white font-mono">
            {metrics?.agents_protected || 1} <span className="text-xs text-slate-400 font-sans font-normal">Active Agent(s)</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">Zero-Trust perimeter enforced</p>
          <div className="absolute -bottom-6 -right-6 w-16 h-16 bg-cyan-500/10 rounded-full blur-xl" />
        </div>

        {/* Metric 2 */}
        <div className="bg-surface border border-surface-border rounded-xl p-4 relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
            <span>EVALUATED & ALLOWED</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-emerald-400 font-mono">
            {metrics?.payments_allowed || 0}{" "}
            <span className="text-xs text-slate-400 font-sans font-normal">/ {metrics?.payments_evaluated || 0}</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">Deterministic check verified</p>
          <div className="absolute -bottom-6 -right-6 w-16 h-16 bg-emerald-500/10 rounded-full blur-xl" />
        </div>

        {/* Metric 3 */}
        <div className="bg-surface border border-surface-border rounded-xl p-4 relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
            <span>NEUTRALIZED THREATS</span>
            <AlertOctagon className="w-4 h-4 text-red-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-red-400 font-mono">
            {metrics?.payments_blocked || 0}{" "}
            <span className="text-xs text-slate-400 font-sans font-normal">Blocked Pre-PayPal</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">0% unauthorized money moved</p>
          <div className="absolute -bottom-6 -right-6 w-16 h-16 bg-red-500/10 rounded-full blur-xl" />
        </div>

        {/* Metric 4 */}
        <div className="bg-surface border border-surface-border rounded-xl p-4 relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
            <span>PREVENTED EXPOSURE</span>
            <DollarSign className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-amber-400 font-mono">
            {formatCurrency(metrics?.blocked_attempted_transaction_value_usd || 0)}
          </div>
          <p className="mt-1 text-[11px] text-slate-400">Attempted attack value prevented</p>
          <div className="absolute -bottom-6 -right-6 w-16 h-16 bg-amber-500/10 rounded-full blur-xl" />
        </div>
      </div>

      {/* Main Grid: Primary Agent Card & Live Sandbox Playground */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols): Active Agent Sentinel Profile & Blast Radius */}
        <div className="lg:col-span-2 space-y-6">
          {/* Agent Card */}
          <div className="bg-surface border border-surface-border rounded-xl p-6 relative">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-surface-border pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-bold text-white font-mono">{primaryAgent?.name}</h3>
                  <span className={`px-2.5 py-0.5 rounded text-xs font-mono border ${trustColor}`}>
                    {primaryAgent?.trust_state}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1 font-mono">
                  ID: {primaryAgent?.id} | Owner: {primaryAgent?.owner_id} | Passport: v{primaryAgent?.passport_version}
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2">
                {primaryAgent?.trust_state === "QUARANTINED" ? (
                  <button
                    onClick={() => handleRestore(primaryAgent.id)}
                    disabled={acting}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-sm transition"
                  >
                    <Unlock className="w-3.5 h-3.5" />
                    <span>Restore Agent</span>
                  </button>
                ) : (
                  <button
                    onClick={() => handleQuarantine(primaryAgent?.id)}
                    disabled={acting}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-semibold shadow-sm transition"
                  >
                    <Lock className="w-3.5 h-3.5" />
                    <span>Quarantine Agent</span>
                  </button>
                )}
                <button
                  onClick={() => onNavigateTab("passport")}
                  className="px-3 py-1.5 rounded-lg bg-surface-raised hover:bg-surface-border text-slate-300 text-xs font-semibold border border-surface-border transition"
                >
                  View Passport
                </button>
              </div>
            </div>

            {/* Agent Limits & Constraints Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4 text-xs font-mono">
              <div className="bg-surface-raised/60 p-3 rounded-lg border border-surface-border/50">
                <span className="text-slate-400 block text-[10px]">TX LIMIT</span>
                <span className="text-base font-bold text-cyan-300">
                  {formatCurrency(primaryAgent?.per_transaction_limit || 500)}
                </span>
              </div>
              <div className="bg-surface-raised/60 p-3 rounded-lg border border-surface-border/50">
                <span className="text-slate-400 block text-[10px]">DAILY LIMIT</span>
                <span className="text-base font-bold text-cyan-300">
                  {formatCurrency(primaryAgent?.daily_limit || 1500)}
                </span>
              </div>
              <div className="bg-surface-raised/60 p-3 rounded-lg border border-surface-border/50">
                <span className="text-slate-400 block text-[10px]">APPROVAL THRESHOLD</span>
                <span className="text-base font-bold text-amber-300">&gt; $300.00</span>
              </div>
              <div className="bg-surface-raised/60 p-3 rounded-lg border border-surface-border/50">
                <span className="text-slate-400 block text-[10px]">BEHAVIOR BASELINE</span>
                <span className="text-base font-bold text-emerald-400">NORMAL (Med: $96)</span>
              </div>
            </div>

            {/* Authorized Categories & Capabilities */}
            <div className="mt-4 flex flex-wrap gap-2 text-xs">
              <span className="text-slate-400 text-xs self-center font-mono">Allowed:</span>
              <span className="px-2 py-0.5 rounded bg-blue-950/60 border border-blue-800/40 text-blue-300">
                electronics
              </span>
              <span className="px-2 py-0.5 rounded bg-blue-950/60 border border-blue-800/40 text-blue-300">
                books
              </span>
              <span className="text-slate-400 text-xs self-center font-mono ml-2">Blocked:</span>
              <span className="px-2 py-0.5 rounded bg-red-950/60 border border-red-800/40 text-red-300">
                cryptocurrency
              </span>
              <span className="px-2 py-0.5 rounded bg-red-950/60 border border-red-800/40 text-red-300">
                gift cards
              </span>
            </div>
          </div>

          {/* Financial Blast Radius Analysis */}
          <div className="bg-surface border border-surface-border rounded-xl p-5">
            <div className="flex items-center justify-between border-b border-surface-border pb-3">
              <h4 className="text-sm font-bold text-white font-mono flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-amber-400" />
                FINANCIAL BLAST RADIUS MODEL
              </h4>
              <span className="text-[11px] text-slate-400 font-mono">Continuous Containment</span>
            </div>
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
              <div className="border border-surface-border p-3 rounded-lg bg-surface-raised/30">
                <span className="text-slate-400 block">Single Transaction Cap</span>
                <span className="text-lg font-bold text-white mt-1 block">
                  {formatCurrency(primaryAgent?.per_transaction_limit || 500)}
                </span>
                <p className="text-[10px] text-slate-500 mt-1">Maximum financial drift per single checkout</p>
              </div>
              <div className="border border-surface-border p-3 rounded-lg bg-surface-raised/30">
                <span className="text-slate-400 block">24h Fleet Ceiling</span>
                <span className="text-lg font-bold text-cyan-300 mt-1 block">
                  {formatCurrency(primaryAgent?.daily_limit || 1500)}
                </span>
                <p className="text-[10px] text-slate-500 mt-1">Deterministic cumulative ceiling</p>
              </div>
              <div className="border border-surface-border p-3 rounded-lg bg-surface-raised/30">
                <span className="text-slate-400 block">Attack Prevention Status</span>
                <span className="text-lg font-bold text-emerald-400 mt-1 block">ACTIVE GUARD</span>
                <p className="text-[10px] text-slate-500 mt-1">PayPal Sandbox blocked on anomalies</p>
              </div>
            </div>
          </div>

          {/* Recent Legitimate Activity Feed */}
          <div className="bg-surface border border-surface-border rounded-xl p-5">
            <div className="flex items-center justify-between border-b border-surface-border pb-3">
              <h4 className="text-sm font-bold text-white font-mono flex items-center gap-2">
                <Activity className="w-4 h-4 text-cyan-400" />
                RECENT ACTIVITY &amp; PAYMENTS
              </h4>
              <button
                onClick={() => onNavigateTab("audit_receipts")}
                className="text-xs text-brand-cyan hover:underline font-mono"
              >
                View Tamper-Evident Log &rarr;
              </button>
            </div>
            <div className="mt-3 divide-y divide-surface-border">
              {[
                { amt: 129.0, item: "Samsung 980 Pro SSD 1TB", decision: "ALLOW", status: "COMPLETED", date: "4 days ago" },
                { amt: 89.0, item: "Mechanical Ergonomic Keyboard", decision: "ALLOW", status: "COMPLETED", date: "2 days ago" },
                { amt: 199.0, item: "Dell 27-inch 4K Monitor", decision: "ALLOW", status: "COMPLETED", date: "1 day ago" },
                { amt: 49.0, item: "Computer Architecture Handbook", decision: "ALLOW", status: "COMPLETED", date: "6 days ago" }
              ].map((tx, idx) => (
                <div key={idx} className="py-2.5 flex items-center justify-between text-xs font-mono">
                  <div>
                    <span className="font-semibold text-white">{tx.item}</span>
                    <span className="text-slate-500 ml-2">{tx.date}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-white font-bold">{formatCurrency(tx.amt)}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-950/60 text-emerald-300 border border-emerald-800/40">
                      {tx.decision}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column (1 Col): Live Interactive Agent Payment Dispatcher */}
        <div className="space-y-6">
          <div className="bg-surface border border-surface-border rounded-xl p-5 shadow-lg">
            <div className="flex items-center justify-between border-b border-surface-border pb-3">
              <h4 className="text-sm font-bold text-white font-mono flex items-center gap-2">
                <Zap className="w-4 h-4 text-yellow-400" />
                LIVE AGENT PAYMENT GATEWAY
              </h4>
            </div>
            <p className="text-xs text-slate-400 mt-2">
              Dispatch an autonomous payment intent to test the end-to-end Zero-Trust evaluation &amp; PayPal Sandbox flow.
            </p>

            <form onSubmit={handleLivePaymentTest} className="mt-4 space-y-3 text-xs font-mono">
              <div>
                <label className="text-slate-300 block mb-1">User Intent Goal</label>
                <input
                  type="text"
                  value={liveGoal}
                  onChange={(e) => setLiveGoal(e.target.value)}
                  className="w-full bg-surface-raised border border-surface-border rounded px-3 py-2 text-white focus:outline-none focus:border-cyan-400"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-slate-300 block mb-1">Amount ($ USD)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={liveAmount}
                    onChange={(e) => setLiveAmount(e.target.value)}
                    className="w-full bg-surface-raised border border-surface-border rounded px-3 py-2 text-white focus:outline-none focus:border-cyan-400"
                  />
                </div>
                <div>
                  <label className="text-slate-300 block mb-1">Category</label>
                  <select
                    value={liveCategory}
                    onChange={(e) => setLiveCategory(e.target.value)}
                    className="w-full bg-surface-raised border border-surface-border rounded px-3 py-2 text-white focus:outline-none focus:border-cyan-400"
                  >
                    <option value="electronics">electronics</option>
                    <option value="books">books</option>
                    <option value="cryptocurrency">cryptocurrency (BLOCKED)</option>
                    <option value="gift cards">gift cards (BLOCKED)</option>
                    <option value="apparel">apparel</option>
                  </select>
                </div>
              </div>

              <button
                type="submit"
                disabled={executingPayPal}
                className="w-full mt-2 py-2 rounded-lg bg-gradient-to-r from-brand-blue to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white font-bold transition flex items-center justify-center gap-2 shadow-md"
              >
                {executingPayPal ? (
                  <>
                    <Clock className="w-4 h-4 animate-spin" />
                    <span>Evaluating &amp; Executing...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-white" />
                    <span>Dispatch Intent to SentinelX</span>
                  </>
                )}
              </button>
            </form>

            {/* Live Result Display */}
            {liveResult && (
              <div className="mt-4 p-3 rounded-lg bg-surface-raised/80 border border-surface-border text-xs font-mono space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">SentinelX Decision:</span>
                  <span
                    className={`font-bold px-2 py-0.5 rounded text-[11px] ${
                      liveResult.decision === "ALLOW"
                        ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                        : liveResult.decision === "STEP-UP"
                        ? "bg-amber-950 text-amber-300 border border-amber-800"
                        : "bg-red-950 text-red-300 border border-red-800"
                    }`}
                  >
                    {liveResult.decision}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Risk Assessment:</span>
                  <span className="text-white font-semibold">
                    {liveResult.overall_risk} ({liveResult.risk_score}/100)
                  </span>
                </div>

                {liveResult.paypal_order && (
                  <div className="pt-2 border-t border-surface-border">
                    <span className="text-[#00d2ff] font-bold block mb-1">✓ PayPal Sandbox Order Created</span>
                    <span className="text-slate-300 block text-[11px] truncate">
                      ID: {liveResult.paypal_order.id}
                    </span>
                    <span className="text-emerald-400 block text-[10px]">
                      Capture Status: {liveResult.paypal_order.status}
                    </span>
                  </div>
                )}

                {liveResult.security_receipt && (
                  <div className="pt-2 border-t border-surface-border">
                    <span className="text-slate-400 block text-[10px]">TAMPER-SEAL RECEIPT</span>
                    <span className="text-cyan-300 block text-[10px] truncate">
                      {liveResult.security_receipt.receipt_id}
                    </span>
                  </div>
                )}

                <p className="text-[11px] text-slate-300 italic pt-1">{liveResult.explanation}</p>
              </div>
            )}
          </div>

          {/* Quick Attack Lab Launch Teaser */}
          <div className="bg-surface border border-surface-border rounded-xl p-5">
            <h4 className="text-sm font-bold text-white font-mono flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-red-400" />
              ATTACK LAB SIMULATOR
            </h4>
            <p className="text-xs text-slate-400 mt-2">
              Launch live attacks: Prompt Injection, Tool Poisoning, Capability Escalation, Replay Attacks, and Destination Swaps.
            </p>
            <button
              onClick={() => onNavigateTab("attack_lab")}
              className="w-full mt-4 py-2 rounded-lg bg-surface-raised hover:bg-surface-border border border-surface-border text-cyan-300 font-semibold text-xs transition"
            >
              Open Interactive Attack Lab (20 Attacks) &rarr;
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

