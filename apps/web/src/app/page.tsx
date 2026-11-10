"use client";

import React, { useState, useEffect } from "react";
import { Header } from "../components/Header";
import { DashboardView } from "../components/DashboardView";
import { AttackLabView } from "../components/AttackLabView";
import { RedTeamView } from "../components/RedTeamView";
import { DecisionGraphView } from "../components/DecisionGraphView";
import { PassportView } from "../components/PassportView";
import { ApprovalCenterView } from "../components/ApprovalCenterView";
import { PolicyBuilderView } from "../components/PolicyBuilderView";
import { AnalystCopilotView } from "../components/AnalystCopilotView";
import { AuditReceiptsView } from "../components/AuditReceiptsView";
import {
  fetchMetrics,
  fetchAgents,
  fetchSecurityEvents,
  verifyAuditChain,
  fetchAttackScenarios,
} from "../lib/api";

export default function Home() {
  const [activeTab, setActiveTab] = useState<string>("dashboard");
  const [metrics, setMetrics] = useState<any>(null);
  const [agents, setAgents] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [chainValid, setChainValid] = useState<boolean>(true);
  const [globalFreeze, setGlobalFreeze] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  const loadData = async () => {
    try {
      const [m, a, ev, sc, ch] = await Promise.all([
        fetchMetrics().catch(() => ({
          agents_protected: 1,
          payments_evaluated: 4,
          payments_allowed: 4,
          payments_blocked: 0,
          threats_detected: 0,
          blocked_attempted_transaction_value_usd: 0,
        })),
        fetchAgents().catch(() => [
          {
            id: "ShoppingAgent-42",
            name: "ShoppingAgent-42",
            owner_id: "Alice",
            trust_state: "TRUSTED",
            passport_version: 1,
            per_transaction_limit: 500,
            daily_limit: 1500,
            capabilities: ["search_products", "cart_management", "initiate_merchant_payments"],
          },
        ]),
        fetchSecurityEvents(30).catch(() => []),
        fetchAttackScenarios().catch(() => []),
        verifyAuditChain().catch(() => ({ is_chain_valid: true })),
      ]);

      setMetrics(m);
      setAgents(a);
      setEvents(ev);
      setScenarios(sc);
      setChainValid(ch.is_chain_valid);
      setGlobalFreeze(!!m.global_freeze_active);
    } catch (err) {
      console.error("Data load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-[#080b11] text-slate-100 flex flex-col font-sans">
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        globalFreeze={globalFreeze}
        setGlobalFreeze={setGlobalFreeze}
        chainValid={chainValid}
        onRefresh={loadData}
        pendingApprovalsCount={metrics?.payments_requiring_approval || 0}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {loading ? (
          <div className="flex items-center justify-center h-64 text-slate-400 font-mono text-xs">
            Connecting to SentinelX Zero-Trust Security Gateway...
          </div>
        ) : (
          <>
            {activeTab === "dashboard" && (
              <DashboardView
                metrics={metrics}
                agents={agents}
                recentEvents={events}
                onRefresh={loadData}
                onNavigateTab={(tab) => setActiveTab(tab)}
              />
            )}

            {activeTab === "attack_lab" && (
              <AttackLabView
                scenarios={scenarios}
                onRefresh={loadData}
                onNavigateTab={(tab) => setActiveTab(tab)}
              />
            )}

            {activeTab === "red_team" && <RedTeamView />}

            {activeTab === "decision_graph" && <DecisionGraphView />}

            {activeTab === "passport" && (
              <PassportView agents={agents} onRefresh={loadData} />
            )}

            {activeTab === "approvals" && (
              <ApprovalCenterView onRefresh={loadData} />
            )}

            {activeTab === "policies" && <PolicyBuilderView />}

            {activeTab === "analyst" && <AnalystCopilotView />}

            {activeTab === "audit_receipts" && (
              <AuditReceiptsView
                events={events}
                chainValid={chainValid}
                onRefresh={loadData}
              />
            )}
          </>
        )}
      </main>

      <footer className="border-t border-surface-border/60 py-4 text-center font-mono text-[11px] text-slate-500">
        SentinelX — Zero-Trust Security Layer for Autonomous Payment Agents • Built for the PayPal AI Hackathon
      </footer>
    </div>
  );
}
