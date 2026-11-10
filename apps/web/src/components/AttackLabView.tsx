"use client";

import React, { useState } from "react";
import {
  ShieldAlert,
  Play,
  RotateCcw,
  CheckCircle2,
  XCircle,
  AlertOctagon,
  Clock,
  Layers,
  ChevronRight,
  Zap,
  Info
} from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import { simulateAttack } from "@/lib/api";

interface AttackLabViewProps {
  scenarios: any[];
  onRefresh: () => void;
  onNavigateTab: (tab: string) => void;
}

export function AttackLabView({ scenarios, onRefresh, onNavigateTab }: AttackLabViewProps) {
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>(scenarios[0]?.id || "attack_prompt_injection");
  const [filterCategory, setFilterCategory] = useState<string>("ALL");
  const [simulating, setSimulating] = useState<boolean>(false);
  const [activeSimulationResult, setActiveSimulationResult] = useState<any>(null);
  const [simStepIndex, setSimStepIndex] = useState<number>(0);

  const selectedScenario = scenarios.find((s) => s.id === selectedScenarioId) || scenarios[0];

  const categories = ["ALL", "INJECTION", "MERCHANT", "CAPABILITY", "POLICY", "REPLAY", "SUBSCRIPTION", "BEHAVIOR", "TOOL_MCP", "VELOCITY"];

  const filteredScenarios = scenarios.filter((s) => {
    if (filterCategory === "ALL") return true;
    return s.category === filterCategory;
  });

  const handleLaunchAttack = async (scenarioId: string) => {
    try {
      setSimulating(true);
      setActiveSimulationResult(null);
      setSimStepIndex(0);

      // Simulate sequential step progression in the UI
      for (let i = 1; i <= 5; i++) {
        await new Promise((r) => setTimeout(r, 220));
        setSimStepIndex(i);
      }

      const res = await simulateAttack(scenarioId);
      setActiveSimulationResult(res);
      onRefresh();
    } catch (err: any) {
      alert("Attack simulation error: " + err.message);
    } finally {
      setSimulating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-surface-border pb-4">
        <div>
          <h2 className="text-xl font-bold text-white font-mono flex items-center gap-2">
            <ShieldAlert className="w-6 h-6 text-red-500" />
            ATTACK LAB — ADVERSARIAL SIMULATION ARENA
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            20 real-world attack classes targeting autonomous AI payment agents. Zero-Trust pre-execution defense.
          </p>
        </div>

        {/* Category Filter Pills */}
        <div className="flex flex-wrap gap-1 text-xs font-mono">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setFilterCategory(cat)}
              className={`px-2.5 py-1 rounded text-[11px] transition ${
                filterCategory === cat
                  ? "bg-brand-blue text-white"
                  : "bg-surface text-slate-400 hover:text-white border border-surface-border"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Main Split Grid: Left 20 Attack List | Right Interactive Stage */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (5 Cols): Scenarios Picker */}
        <div className="lg:col-span-5 space-y-2 max-h-[750px] overflow-y-auto pr-1">
          {filteredScenarios.map((sc) => {
            const isSelected = sc.id === selectedScenarioId;
            return (
              <div
                key={sc.id}
                onClick={() => setSelectedScenarioId(sc.id)}
                className={`p-3.5 rounded-xl border cursor-pointer transition text-xs font-mono ${
                  isSelected
                    ? "bg-surface-raised border-red-500/80 shadow-md glow-crimson/20"
                    : "bg-surface border-surface-border hover:bg-surface-raised/50"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white text-xs truncate max-w-[220px]">{sc.name}</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] uppercase ${
                      sc.severity === "CRITICAL"
                        ? "bg-red-950 text-red-300 border border-red-800"
                        : sc.severity === "HIGH"
                        ? "bg-amber-950 text-amber-300 border border-amber-800"
                        : "bg-blue-950 text-blue-300 border border-blue-800"
                    }`}
                  >
                    {sc.category}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">{sc.description}</p>
                <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400 border-t border-surface-border/60 pt-2">
                  <span>Target: {formatCurrency(sc.requested_amount)}</span>
                  <span className="text-cyan-400 flex items-center gap-1">
                    Select &rarr;
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right Column (7 Cols): Selected Attack Simulation Stage & Timeline */}
        <div className="lg:col-span-7 space-y-6">
          <div className="bg-surface border border-surface-border rounded-xl p-6">
            <div className="flex items-center justify-between border-b border-surface-border pb-4">
              <div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-red-950/60 text-red-400 border border-red-800/40 uppercase">
                  {selectedScenario?.category} ATTACK
                </span>
                <h3 className="text-lg font-bold text-white font-mono mt-1">{selectedScenario?.name}</h3>
              </div>

              {/* Action Buttons: Launch Simulation and Replay */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleLaunchAttack(selectedScenario.id)}
                  disabled={simulating}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white font-bold text-xs uppercase tracking-wider glow-crimson transition"
                >
                  {simulating ? <Clock className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-white" />}
                  <span>Launch Simulation</span>
                </button>

                {activeSimulationResult && (
                  <button
                    onClick={() => handleLaunchAttack(selectedScenario.id)}
                    disabled={simulating}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-surface-raised hover:bg-surface-border border border-surface-border text-slate-300 text-xs font-semibold transition"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Replay Attack</span>
                  </button>
                )}
              </div>
            </div>

            {/* Attack Details */}
            <div className="mt-4 space-y-3 text-xs font-mono">
              <div className="p-3 rounded-lg bg-surface-raised/60 border border-surface-border/60">
                <span className="text-slate-400 block text-[10px]">ORIGINAL USER TASK</span>
                <span className="text-white font-semibold">{selectedScenario?.user_goal}</span>
              </div>

              <div className="p-3 rounded-lg bg-surface-raised/60 border border-surface-border/60">
                <span className="text-slate-400 block text-[10px]">ADVERSARIAL ATTACK VECTOR</span>
                <p className="text-slate-300 mt-1">{selectedScenario?.description}</p>
              </div>

              <div className="p-3 rounded-lg bg-surface-raised/60 border border-surface-border/60">
                <span className="text-slate-400 block text-[10px]">EXPECTED SENTINELX ZERO-TRUST DEFENSE</span>
                <p className="text-cyan-300 mt-1">{selectedScenario?.expected_defense}</p>
              </div>
            </div>

            {/* Real-time Attack Progression Pipeline (Section 39) */}
            <div className="mt-6 border-t border-surface-border pt-4">
              <h4 className="text-xs font-bold text-white font-mono uppercase tracking-wider mb-3">
                ATTACK PROGRESSION PIPELINE
              </h4>

              <div className="space-y-2 text-xs font-mono">
                {[
                  { title: "1. Normal Agent Dispatched", desc: "Agent initialized with Ed25519 identity & Passport", passed: simStepIndex >= 1 },
                  { title: "2. Malicious Input / Injected Vector", desc: "Untrusted webpage script or poisoned MCP tool executes", passed: simStepIndex >= 2 },
                  { title: "3. Agent Deviation / Plan Change", desc: "Agent attempts unauthorized transaction modification", passed: simStepIndex >= 3 },
                  { title: "4. SentinelX Gateway Interception", desc: "Zero-Trust policy, intent drift, and provenance check", passed: simStepIndex >= 4 },
                  { title: "5. Enforcement: Payment Blocked & Quarantined", desc: "Zero calls to PayPal API | Tamper-evident audit logged", passed: simStepIndex >= 5 || !!activeSimulationResult }
                ].map((step, idx) => (
                  <div
                    key={idx}
                    className={`p-2.5 rounded-lg border flex items-center justify-between transition ${
                      step.passed
                        ? idx === 4
                          ? "bg-red-950/40 border-red-800 text-red-300"
                          : "bg-surface-raised border-surface-border text-slate-200"
                        : "bg-surface/30 border-surface-border/30 text-slate-600"
                    }`}
                  >
                    <div>
                      <span className="font-bold block">{step.title}</span>
                      <span className="text-[11px] text-slate-400">{step.desc}</span>
                    </div>
                    {step.passed ? (
                      idx === 4 ? (
                        <AlertOctagon className="w-5 h-5 text-red-400" />
                      ) : (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      )
                    ) : (
                      <div className="w-4 h-4 rounded-full border border-slate-700" />
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Live Attack Interception Evidence */}
            {activeSimulationResult && (
              <div className="mt-6 p-4 rounded-xl bg-red-950/30 border border-red-800/80 space-y-3 font-mono text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-red-400 text-sm flex items-center gap-2">
                    <AlertOctagon className="w-4 h-4 text-red-400" />
                    ATTACK DETECTED &amp; NEUTRALIZED
                  </span>
                  <span className="px-2.5 py-0.5 rounded bg-red-900 text-white font-bold text-xs uppercase">
                    {activeSimulationResult.decision}
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] pt-2 border-t border-red-900/40">
                  <div>
                    <span className="text-slate-400 block">INTENT ALIGNMENT</span>
                    <span className="text-white font-bold">{activeSimulationResult.scores.intent}/100</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block">PROVENANCE SCORE</span>
                    <span className="text-white font-bold">{activeSimulationResult.scores.provenance}/100</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block">BEHAVIOR ANOMALY</span>
                    <span className="text-white font-bold">{activeSimulationResult.scores.behavior}/100</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block">RISK SCORE</span>
                    <span className="text-red-400 font-bold">{activeSimulationResult.scores.risk_score}/100</span>
                  </div>
                </div>

                {/* Reasons List */}
                <div className="pt-2">
                  <span className="text-slate-400 block text-[10px] mb-1">EVIDENCE SIGNALS TRIGGERED:</span>
                  <ul className="space-y-1">
                    {activeSimulationResult.reasons.map((r: string, idx: number) => (
                      <li key={idx} className="text-red-300 flex items-start gap-1.5 text-[11px]">
                        <span className="text-red-500 font-bold">•</span>
                        <span>{r}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Audit Hash Seal */}
                <div className="pt-2 border-t border-red-900/40 flex items-center justify-between text-[10px] text-slate-400">
                  <span>AUDIT EVENT: {activeSimulationResult.audit_event_id}</span>
                  <span className="text-cyan-400 font-mono truncate max-w-[200px]">
                    HASH: {activeSimulationResult.audit_event_hash}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

