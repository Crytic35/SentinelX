"use client";

import React, { useState } from "react";
import { Shield, ShieldAlert, ShieldCheck, Power, RefreshCw, CheckCircle2, AlertTriangle, Terminal } from "lucide-react";
import { toggleGlobalFreeze } from "@/lib/api";

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  globalFreeze: boolean;
  setGlobalFreeze: (freeze: boolean) => void;
  chainValid: boolean;
  onRefresh: () => void;
  pendingApprovalsCount: number;
}

export function Header({
  activeTab,
  setActiveTab,
  globalFreeze,
  setGlobalFreeze,
  chainValid,
  onRefresh,
  pendingApprovalsCount,
}: HeaderProps) {
  const [freezing, setFreezing] = useState(false);

  const handleToggleFreeze = async () => {
    try {
      setFreezing(true);
      const res = await toggleGlobalFreeze(!globalFreeze);
      setGlobalFreeze(res.global_freeze);
    } catch (err) {
      alert("Failed to toggle global freeze: " + err);
    } finally {
      setFreezing(false);
    }
  };

  const navItems = [
    { id: "dashboard", label: "Dashboard" },
    { id: "attack_lab", label: "Attack Lab (20)" },
    { id: "red_team", label: "Red / Blue Team" },
    { id: "decision_graph", label: "Decision Graph" },
    { id: "passport", label: "Agent Passport" },
    { id: "approvals", label: "Approval Center", badge: pendingApprovalsCount },
    { id: "policies", label: "Policy Engine & NL" },
    { id: "analyst", label: "AI Copilot" },
    { id: "audit_receipts", label: "Audit & Receipts" },
  ];

  return (
    <header className="border-b border-surface-border bg-surface/90 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Tagline */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-tr from-brand-blue to-cyan-400 flex items-center justify-center glow-blue">
              <Shield className="w-6 h-6 text-white stroke-[2.5]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold tracking-tight text-xl text-white font-mono">
                  SENTINEL<span className="text-cyan-400">X</span>
                </span>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-brand-blue/20 text-cyan-300 border border-brand-blue/30 uppercase tracking-wider">
                  Zero-Trust
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block truncate max-w-sm">
                AI agents can spend money. SentinelX makes sure they don&apos;t spend yours.
              </p>
            </div>
          </div>

          {/* Right Action Controls: PayPal Sandbox Pill, Hash Chain Integrity, Kill Switch */}
          <div className="flex items-center gap-3">
            {/* PayPal Sandbox Status */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#003087]/20 border border-[#0070ba]/40 text-[#00d2ff] text-xs font-mono">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>PayPal Sandbox</span>
            </div>

            {/* Audit Chain Verification Pill */}
            <div className={`hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono border ${
              chainValid
                ? "bg-emerald-950/40 text-emerald-300 border-emerald-800/40"
                : "bg-red-950/40 text-red-300 border-red-800/40 animate-pulse"
            }`}>
              {chainValid ? (
                <>
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Audit Chain: Tamper-Free</span>
                </>
              ) : (
                <>
                  <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
                  <span>Tamper Alert</span>
                </>
              )}
            </div>

            {/* Refresh Button */}
            <button
              onClick={onRefresh}
              title="Refresh Data"
              className="p-1.5 rounded-md hover:bg-surface-raised border border-surface-border text-slate-400 hover:text-white transition"
            >
              <RefreshCw className="w-4 h-4" />
            </button>

            {/* Global Kill Switch */}
            <button
              onClick={handleToggleFreeze}
              disabled={freezing}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold uppercase tracking-wider transition ${
                globalFreeze
                  ? "bg-red-600 hover:bg-red-700 text-white glow-crimson animate-pulse"
                  : "bg-surface-raised hover:bg-red-900/30 text-red-400 border border-red-800/40"
              }`}
            >
              <Power className="w-3.5 h-3.5" />
              <span>{globalFreeze ? "KILL SWITCH ACTIVE" : "Freeze Payments"}</span>
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex space-x-1 overflow-x-auto pb-2 pt-1 border-t border-surface-border/60 scrollbar-none">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition ${
                  isActive
                    ? "bg-brand-blue text-white shadow-sm"
                    : "text-slate-400 hover:text-slate-200 hover:bg-surface-raised"
                }`}
              >
                <span>{item.label}</span>
                {item.badge !== undefined && item.badge > 0 && (
                  <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-amber-500 text-black font-bold">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
}

