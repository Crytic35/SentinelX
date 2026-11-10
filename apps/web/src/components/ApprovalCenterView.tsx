"use client";

import React, { useState } from "react";
import { UserCheck, ShieldAlert, CheckCircle2, XCircle, Lock, AlertTriangle, ArrowRight, Clock } from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import { handleHumanApproval, executePayPalOrder, capturePayPalOrder } from "@/lib/api";

interface ApprovalCenterViewProps {
  onRefresh: () => void;
}

export function ApprovalCenterView({ onRefresh }: ApprovalCenterViewProps) {
  const [acting, setActing] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // Example pending step-up request in human approval queue
  const [pendingItems, setPendingItems] = useState<any[]>([
    {
      id: "pi_stepup_demo_882",
      agent_id: "ShoppingAgent-42",
      user_goal: "Buy developer 4K workstation monitor under $400",
      purpose: "Dell UltraSharp 27-inch 4K Monitor",
      amount: 350.0,
      currency: "USD",
      category: "electronics",
      merchant_id: "merch_bestbuy_01",
      merchant_name: "Best Buy Official",
      risk_score: 48.0,
      reasons: [
        "Transaction amount $350.00 exceeds standard autonomous approval threshold of $300.00"
      ],
      created_at: "Just now"
    }
  ]);

  const handleAction = async (itemId: string, action: string) => {
    try {
      setActing(true);
      setActionMessage(null);
      const res = await handleHumanApproval(itemId, action, "ONCE", "Approved via SecOps Human Center");

      if (action === "APPROVE_ONCE") {
        // Execute PayPal sandbox flow automatically on human sign-off
        try {
          const order = await executePayPalOrder(itemId);
          await capturePayPalOrder(itemId, order.paypal_order_id);
          setActionMessage(`Transaction authorized and executed on PayPal Sandbox! PayPal Order: ${order.paypal_order_id}`);
        } catch {
          setActionMessage("Transaction authorized by human operator. Ready for payment dispatch.");
        }
      } else {
        setActionMessage(`Action '${action}' applied to transaction.`);
      }

      setPendingItems((prev) => prev.filter((i) => i.id !== itemId));
      onRefresh();
    } catch (err: any) {
      alert("Approval action error: " + err.message);
    } finally {
      setActing(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-surface-border pb-4">
        <div>
          <h2 className="text-xl font-bold text-white font-mono flex items-center gap-2">
            <UserCheck className="w-6 h-6 text-amber-400" />
            HUMAN APPROVAL ESCALATION CENTER
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Zero-Trust Human-in-the-Loop boundary. Review transactions exceeding autonomous spending thresholds or novel merchant context.
          </p>
        </div>
        <span className="text-xs font-mono text-amber-400 border border-amber-800/40 px-3 py-1 rounded bg-amber-950/40">
          {pendingItems.length} Pending Review
        </span>
      </div>

      {actionMessage && (
        <div className="p-3.5 rounded-lg bg-emerald-950/50 border border-emerald-800 text-emerald-300 text-xs font-mono flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>{actionMessage}</span>
        </div>
      )}

      {pendingItems.length > 0 ? (
        <div className="space-y-4">
          {pendingItems.map((item) => (
            <div key={item.id} className="bg-surface border border-surface-border rounded-xl p-6 font-mono text-xs space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-surface-border pb-3">
                <div>
                  <span className="text-[10px] text-slate-400 block">INTENT ID: {item.id}</span>
                  <span className="text-white font-bold text-sm">{item.purpose}</span>
                </div>
                <div className="text-right">
                  <span className="text-lg font-bold text-amber-300">{formatCurrency(item.amount)}</span>
                  <span className="text-[10px] text-slate-400 block">{item.currency}</span>
                </div>
              </div>

              {/* Review Details Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                <div className="p-3 rounded-lg bg-surface-raised border border-surface-border">
                  <span className="text-slate-400 block text-[10px]">ORIGINAL USER GOAL</span>
                  <p className="text-white mt-1">{item.user_goal}</p>
                </div>
                <div className="p-3 rounded-lg bg-surface-raised border border-surface-border">
                  <span className="text-slate-400 block text-[10px]">AGENT &amp; MERCHANT</span>
                  <p className="text-cyan-300 mt-1">{item.agent_id}</p>
                  <p className="text-slate-300 text-[11px] mt-0.5">{item.merchant_name} ({item.merchant_id})</p>
                </div>
                <div className="p-3 rounded-lg bg-surface-raised border border-surface-border">
                  <span className="text-slate-400 block text-[10px]">ESCALATION TRIGGER</span>
                  <p className="text-amber-300 mt-1">{item.reasons[0]}</p>
                </div>
              </div>

              {/* Action Buttons: Narrowly Scoped Enforcement */}
              <div className="flex flex-wrap items-center justify-end gap-2 pt-2 border-t border-surface-border">
                <button
                  onClick={() => handleAction(item.id, "REJECT")}
                  disabled={acting}
                  className="px-3.5 py-2 rounded-lg bg-surface-raised hover:bg-surface-border text-slate-300 font-semibold transition"
                >
                  Reject Transaction
                </button>
                <button
                  onClick={() => handleAction(item.id, "RESTRICT_AGENT")}
                  disabled={acting}
                  className="px-3.5 py-2 rounded-lg bg-amber-900/40 hover:bg-amber-900/70 border border-amber-800 text-amber-300 font-semibold transition"
                >
                  Restrict Agent
                </button>
                <button
                  onClick={() => handleAction(item.id, "QUARANTINE")}
                  disabled={acting}
                  className="px-3.5 py-2 rounded-lg bg-red-900/40 hover:bg-red-900/70 border border-red-800 text-red-300 font-semibold transition"
                >
                  Quarantine Agent
                </button>
                <button
                  onClick={() => handleAction(item.id, "APPROVE_ONCE")}
                  disabled={acting}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold glow-emerald transition flex items-center gap-1.5 shadow-md"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Approve This Payment Once &amp; Execute PayPal</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-surface border border-surface-border rounded-xl p-12 text-center font-mono text-xs">
          <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto mb-3" />
          <h3 className="text-white font-bold text-sm">Human Approval Queue Clean</h3>
          <p className="text-slate-400 mt-1 max-w-md mx-auto">
            All pending payment requests have been verified. Any transaction exceeding policy limits will appear here for operator sign-off.
          </p>
        </div>
      )}
    </div>
  );
}

