"use client";

import React, { useState } from "react";
import { KeyRound, Shield, User, CheckCircle2, AlertOctagon, Plus, Copy, Lock, Unlock } from "lucide-react";
import { formatCurrency } from "@/lib/utils";

interface PassportViewProps {
  agents: any[];
  onRefresh: () => void;
}

export function PassportView({ agents, onRefresh }: PassportViewProps) {
  const [selectedAgentId, setSelectedAgentId] = useState<string>(agents[0]?.id || "ShoppingAgent-42");
  const [copiedKey, setCopiedKey] = useState(false);

  const agent = agents.find((a) => a.id === selectedAgentId) || agents[0];

  const handleCopyKey = () => {
    if (agent?.public_key) {
      navigator.clipboard.writeText(agent.public_key);
      setCopiedKey(true);
      setTimeout(() => setCopiedKey(false), 2000);
    }
  };

  const trustStages = ["NEW", "UNVERIFIED", "TRUSTED", "SUSPICIOUS", "RESTRICTED", "QUARANTINED", "REVOKED"];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-surface-border pb-4">
        <div>
          <h2 className="text-xl font-bold text-white font-mono flex items-center gap-2">
            <KeyRound className="w-6 h-6 text-brand-cyan" />
            AGENT PASSPORT &amp; CRYPTOGRAPHIC IDENTITY
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Every AI payment agent holds an immutable, cryptographically signed Passport defining bounded financial authority.
          </p>
        </div>

        {/* Agent Selector */}
        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="text-slate-400">Agent:</span>
          <select
            value={selectedAgentId}
            onChange={(e) => setSelectedAgentId(e.target.value)}
            className="bg-surface border border-surface-border rounded-lg px-3 py-1.5 text-white focus:outline-none focus:border-cyan-400"
          >
            {agents.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name} ({a.trust_state})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Trust Lifecycle Progression Bar (Section 4) */}
      <div className="bg-surface border border-surface-border rounded-xl p-5 font-mono text-xs">
        <h4 className="text-slate-400 text-[10px] uppercase tracking-wider mb-3">AGENT TRUST LIFECYCLE</h4>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
          {trustStages.map((stage) => {
            const isCurrent = agent?.trust_state === stage;
            const isQuarantined = stage === "QUARANTINED" && isCurrent;
            const isRestricted = stage === "RESTRICTED" && isCurrent;

            return (
              <div
                key={stage}
                className={`p-2.5 rounded-lg border text-center transition ${
                  isCurrent
                    ? isQuarantined
                      ? "bg-red-950 border-red-500 text-red-300 font-bold glow-crimson/30"
                      : isRestricted
                      ? "bg-amber-950 border-amber-500 text-amber-300 font-bold glow-amber/30"
                      : "bg-emerald-950 border-emerald-500 text-emerald-300 font-bold glow-emerald/30"
                    : "bg-surface-raised/40 border-surface-border/40 text-slate-600"
                }`}
              >
                <span className="block text-[11px]">{stage}</span>
                {isCurrent && <span className="text-[9px] text-cyan-400 block mt-0.5">CURRENT</span>}
              </div>
            );
          })}
        </div>
      </div>

      {/* Passport Credential Card */}
      <div className="bg-gradient-to-br from-surface to-surface-raised border border-cyan-800/40 rounded-xl p-6 relative overflow-hidden shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-surface-border/80 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-brand-blue to-cyan-400 flex items-center justify-center glow-blue">
              <Shield className="w-7 h-7 text-white stroke-[2.5]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-white font-mono">{agent?.name}</h3>
                <span className="text-xs px-2 py-0.5 rounded bg-brand-blue/30 text-cyan-300 border border-brand-blue/50 font-mono">
                  PASSPORT v{agent?.passport_version || 1}
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                Owner ID: {agent?.owner_id} | Agent ID: {agent?.id}
              </p>
            </div>
          </div>

          <div className="text-right font-mono text-xs">
            <span className="text-slate-400 block text-[10px]">ED25519 VERIFICATION</span>
            <span className="text-emerald-400 font-bold flex items-center gap-1 justify-end">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              Cryptographically Signed
            </span>
          </div>
        </div>

        {/* Public Key Display */}
        <div className="mt-4 p-3 rounded-lg bg-[#080b11] border border-surface-border font-mono text-xs">
          <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
            <span>ED25519 PUBLIC KEY</span>
            <button
              onClick={handleCopyKey}
              className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
            >
              <Copy className="w-3 h-3" />
              <span>{copiedKey ? "Copied!" : "Copy"}</span>
            </button>
          </div>
          <span className="text-cyan-300 break-all select-all block text-[11px]">
            {agent?.public_key || "a9f848b57d42cf29e84b8401ef6c11739c91629851486bc0521e102f4d67e108"}
          </span>
        </div>

        {/* Passport Constraints & Rules Grid */}
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 font-mono text-xs">
          <div className="p-3 rounded-lg bg-surface-raised border border-surface-border">
            <span className="text-slate-400 block text-[10px]">SPENDING LIMITS</span>
            <span className="text-white font-bold block mt-1">
              {formatCurrency(agent?.per_transaction_limit || 500)} / tx
            </span>
            <span className="text-slate-300 block text-[11px]">
              {formatCurrency(agent?.daily_limit || 1500)} / 24h ceiling
            </span>
          </div>

          <div className="p-3 rounded-lg bg-surface-raised border border-surface-border">
            <span className="text-slate-400 block text-[10px]">APPROVAL THRESHOLDS</span>
            <span className="text-amber-300 font-bold block mt-1">
              &gt; $300.00 mandates human review
            </span>
            <span className="text-slate-400 block text-[11px]">
              New merchants &amp; recurring subscriptions require review
            </span>
          </div>

          <div className="p-3 rounded-lg bg-surface-raised border border-surface-border">
            <span className="text-slate-400 block text-[10px]">GEOGRAPHIC RESTRICTIONS</span>
            <span className="text-white font-bold block mt-1">Allowed: US, IN, GB, EU, CA</span>
            <span className="text-slate-400 block text-[11px]">Fail-closed on unauthorized regions</span>
          </div>
        </div>

        {/* Capabilities List */}
        <div className="mt-4 border-t border-surface-border/60 pt-3 flex flex-wrap items-center gap-2 text-xs font-mono">
          <span className="text-slate-400 text-[11px]">Delegated Capabilities:</span>
          {(agent?.capabilities || ["search_products", "cart_management", "initiate_merchant_payments", "view_orders"]).map((cap: string, i: number) => (
            <span key={i} className="px-2.5 py-1 rounded-md bg-cyan-950/40 border border-cyan-800/40 text-cyan-300 text-[11px]">
              {cap}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

