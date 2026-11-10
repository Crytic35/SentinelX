"use client";

import React, { useState } from "react";
import { Terminal, Send, Bot, User, Sparkles, ShieldAlert, CheckCircle2 } from "lucide-react";
import { querySecurityAnalyst } from "@/lib/api";

export function AnalystCopilotView() {
  const [messages, setMessages] = useState<any[]>([
    {
      sender: "copilot",
      text: "Hello, SecOps Operator. I am the SentinelX AI Security Analyst. I interrogate structured tamper-evident audit logs and explain security events. How can I assist your investigation today?",
      time: "Just now"
    }
  ]);
  const [inputText, setInputText] = useState("");
  const [loading, setLoading] = useState(false);

  const promptChips = [
    "Why was ShoppingAgent-42 blocked?",
    "Show attacks caused by untrusted tools.",
    "Which agents are currently quarantined?",
    "Summarize today's security incidents."
  ];

  const handleSend = async (queryToRun?: string) => {
    const q = queryToRun || inputText;
    if (!q.trim() || loading) return;

    const userMsg = { sender: "user", text: q, time: new Date().toLocaleTimeString() };
    setMessages((prev) => [...prev, userMsg]);
    setInputText("");
    setLoading(true);

    try {
      const res = await querySecurityAnalyst(q, "ShoppingAgent-42");
      const copilotMsg = {
        sender: "copilot",
        text: res.response,
        time: new Date().toLocaleTimeString()
      };
      setMessages((prev) => [...prev, copilotMsg]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          sender: "copilot",
          text: "Investigation error: " + err.message,
          time: new Date().toLocaleTimeString()
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-surface-border pb-4">
        <div>
          <h2 className="text-xl font-bold text-white font-mono flex items-center gap-2">
            <Terminal className="w-6 h-6 text-brand-cyan" />
            AI SECURITY ANALYST &amp; SEC-OPS COPILOT
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Read-only semantic investigation agent. Interrogates structured tamper-evident audit logs without mutating authorization state.
          </p>
        </div>
      </div>

      {/* Quick Prompts Chips */}
      <div className="flex flex-wrap gap-2 text-xs font-mono">
        <span className="text-slate-400 self-center text-[11px]">Quick Queries:</span>
        {promptChips.map((chip, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(chip)}
            className="px-3 py-1 rounded-full bg-surface hover:bg-surface-raised border border-surface-border text-slate-300 hover:text-cyan-300 transition text-[11px]"
          >
            {chip}
          </button>
        ))}
      </div>

      {/* Chat Thread Container */}
      <div className="bg-surface border border-surface-border rounded-xl p-6 h-[480px] flex flex-col justify-between font-mono text-xs">
        <div className="overflow-y-auto space-y-4 pr-2">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex gap-3 ${m.sender === "user" ? "justify-end" : "justify-start"}`}
            >
              {m.sender === "copilot" && (
                <div className="w-8 h-8 rounded-lg bg-brand-blue/30 border border-brand-blue flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4 text-cyan-300" />
                </div>
              )}
              <div
                className={`max-w-xl p-3.5 rounded-xl whitespace-pre-line text-xs ${
                  m.sender === "user"
                    ? "bg-brand-blue text-white"
                    : "bg-surface-raised border border-surface-border text-slate-200"
                }`}
              >
                {m.text}
                <span className="text-[10px] text-slate-400 block mt-1.5 opacity-70">
                  {m.time}
                </span>
              </div>
              {m.sender === "user" && (
                <div className="w-8 h-8 rounded-lg bg-surface-raised border border-surface-border flex items-center justify-center shrink-0">
                  <User className="w-4 h-4 text-slate-300" />
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex gap-3 justify-start">
              <div className="w-8 h-8 rounded-lg bg-brand-blue/30 border border-brand-blue flex items-center justify-center">
                <Bot className="w-4 h-4 text-cyan-300 animate-spin" />
              </div>
              <div className="p-3 rounded-xl bg-surface-raised border border-surface-border text-slate-400 italic">
                Synthesizing structured security evidence...
              </div>
            </div>
          )}
        </div>

        {/* Input Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="mt-4 flex gap-2 pt-3 border-t border-surface-border"
        >
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Ask anything about security decisions, provenance, or policy violations..."
            className="flex-1 bg-surface-raised border border-surface-border rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-cyan-400 text-xs font-mono"
          />
          <button
            type="submit"
            disabled={loading || !inputText.trim()}
            className="px-4 py-2.5 rounded-lg bg-brand-blue hover:bg-blue-600 disabled:opacity-50 text-white font-bold transition flex items-center gap-1.5"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}

