"use client";

import React, { useState } from "react";
import { ShieldCheck, ShieldAlert, FileText, CheckCircle2, Hash, Lock, Search } from "lucide-react";
import { formatCurrency } from "@/lib/utils";

interface AuditReceiptsViewProps {
  events: any[];
  chainValid: boolean;
  onRefresh: () => void;
}

export function AuditReceiptsView({ events, chainValid, onRefresh }: AuditReceiptsViewProps) {
  const [selectedEvent, setSelectedEvent] = useState<any>(events[0] || null);

  // Sample receipts linking PayPal Order IDs to SentinelX decisions
  const sampleReceipts = [
    {
      receipt_id: "rcpt_982bf71a938c11",
      paypal_order_id: "PAYPAL-SANDBOX-ORDER-49A1B2",
      decision: "ALLOW",
      amount: 129.0,
      currency: "USD",
      agent_id: "ShoppingAgent-42",
      issued_at: "2026-11-10 10:28:14 UTC",
      tamper_seal: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      checks_passed: [
        "Cryptographic Agent Identity Verified",
        "Deterministic Policy Spending Cap Checked",
        "Intent Drift Check Aligned",
        "Tool Provenance Authenticated",
        "PayPal Destination Bound"
      ]
    },
    {
      receipt_id: "rcpt_283cf99d104a77",
      paypal_order_id: "PAYPAL-SANDBOX-ORDER-88B3C4",
      decision: "ALLOW",
      amount: 89.0,
      currency: "USD",
      agent_id: "ShoppingAgent-42",
      issued_at: "2026-11-08 14:15:33 UTC",
      tamper_seal: "8a45e7f60c1d34b8e2194b15093bc141d655f410224b1f4710ca199ef1549ab1",
      checks_passed: [
        "Cryptographic Agent Identity Verified",
        "Deterministic Policy Spending Cap Checked",
        "Intent Drift Check Aligned",
        "Tool Provenance Authenticated",
        "PayPal Destination Bound"
      ]
    }
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-surface-border pb-4">
        <div>
          <h2 className="text-xl font-bold text-white font-mono flex items-center gap-2">
            <Hash className="w-6 h-6 text-brand-cyan" />
            TAMPER-EVIDENT AUDIT TRAIL &amp; SECURITY RECEIPTS
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Append-only hash-chained ledger: hash_n = SHA-256(canonical_json(event_n) + hash_n-1). Cryptographic provenance from instruction to PayPal.
          </p>
        </div>

        {/* Chain Integrity Status Badge */}
        <div
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg font-mono text-xs border ${
            chainValid
              ? "bg-emerald-950/40 text-emerald-300 border-emerald-800/40"
              : "bg-red-950/40 text-red-300 border-red-800/40"
          }`}
        >
          {chainValid ? (
            <>
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Hash Chain: Verified Authentic</span>
            </>
          ) : (
            <>
              <ShieldAlert className="w-4 h-4 text-red-400" />
              <span>Hash Discrepancy Detected!</span>
            </>
          )}
        </div>
      </div>

      {/* Grid: Events Timeline (7 Cols) & Receipts / Hash Inspector (5 Cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Security Events Timeline */}
        <div className="lg:col-span-7 bg-surface border border-surface-border rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-surface-border pb-3">
            <h3 className="text-sm font-bold text-white font-mono">
              TAMPER-EVIDENT EVENT TIMELINE
            </h3>
            <span className="text-[11px] font-mono text-slate-400">
              {events.length} Audited Events
            </span>
          </div>

          <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
            {events.map((ev: any) => {
              const isSelected = selectedEvent?.id === ev.id;
              const isCrit = ev.severity === "CRITICAL" || ev.severity === "HIGH";

              return (
                <div
                  key={ev.id}
                  onClick={() => setSelectedEvent(ev)}
                  className={`p-3 rounded-lg border font-mono text-xs cursor-pointer transition ${
                    isSelected
                      ? "bg-surface-raised border-cyan-400"
                      : isCrit
                      ? "bg-red-950/20 border-red-900/40 hover:bg-red-950/30"
                      : "bg-surface border-surface-border hover:bg-surface-raised"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white text-xs">{ev.event_type}</span>
                    <span
                      className={`px-2 py-0.2 rounded text-[10px] ${
                        isCrit
                          ? "bg-red-950 text-red-300 border border-red-800"
                          : "bg-blue-950 text-blue-300 border border-blue-800"
                      }`}
                    >
                      {ev.severity}
                    </span>
                  </div>
                  <p className="text-slate-300 text-[11px] mt-1">{ev.summary}</p>
                  <div className="mt-2 flex items-center justify-between text-[10px] text-slate-500 border-t border-surface-border/50 pt-1.5">
                    <span>Agent: {ev.agent_id || "System"}</span>
                    <span className="truncate max-w-[200px]">Prev: {ev.previous_hash?.substring(0, 16)}...</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Security Receipt & Cryptographic Seal Viewer */}
        <div className="lg:col-span-5 space-y-6">
          {/* Selected Event Hash Seal Box */}
          <div className="bg-surface border border-surface-border rounded-xl p-5 font-mono text-xs space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-surface-border pb-3">
              <Lock className="w-4 h-4 text-cyan-400" />
              EVENT CRYPTOGRAPHIC SEAL
            </h3>

            {selectedEvent ? (
              <div className="space-y-3">
                <div>
                  <span className="text-slate-400 block text-[10px]">EVENT ID</span>
                  <span className="text-white font-bold">{selectedEvent.id}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">PREVIOUS HASH (H_n-1)</span>
                  <span className="text-cyan-300 break-all select-all block text-[11px] bg-[#080b11] p-2 rounded border border-surface-border">
                    {selectedEvent.previous_hash}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">EVENT HASH (H_n)</span>
                  <span className="text-emerald-300 break-all select-all block text-[11px] bg-[#080b11] p-2 rounded border border-surface-border">
                    {selectedEvent.event_hash}
                  </span>
                </div>
                {selectedEvent.payload && (
                  <div>
                    <span className="text-slate-400 block text-[10px] mb-1">CANONICAL PAYLOAD</span>
                    <div className="bg-[#080b11] p-2.5 rounded text-[10px] text-slate-300 max-h-36 overflow-y-auto">
                      <pre>{JSON.stringify(selectedEvent.payload, null, 2)}</pre>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-slate-500 text-xs">Select an event from the timeline to view its cryptographic chain hashes.</p>
            )}
          </div>

          {/* PayPal Transaction Security Receipts */}
          <div className="bg-surface border border-surface-border rounded-xl p-5 font-mono text-xs space-y-4">
            <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-surface-border pb-3">
              <FileText className="w-4 h-4 text-emerald-400" />
              PAYPAL TRANSACTION SECURITY RECEIPTS
            </h3>

            {sampleReceipts.map((rcpt) => (
              <div key={rcpt.receipt_id} className="p-3.5 rounded-lg bg-surface-raised border border-surface-border space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-cyan-300 font-bold">{rcpt.paypal_order_id}</span>
                  <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800">
                    {rcpt.decision}
                  </span>
                </div>
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-slate-300">{formatCurrency(rcpt.amount, rcpt.currency)}</span>
                  <span className="text-slate-500">{rcpt.issued_at}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[9px]">TAMPER SEAL:</span>
                  <span className="text-[10px] text-cyan-400 truncate block">{rcpt.tamper_seal}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

