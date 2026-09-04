"use client";

import { useState, useRef, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Bot, Send, X, Sparkles, Terminal } from "lucide-react";
import { HudLabel } from "./primitives/Hud";

interface ChatMessage {
  role: "user" | "copilot";
  content: string;
  timestamp: string;
}

const QUICK_PROMPTS = [
  "Site Security Summary",
  "Latest Critical Alerts",
  "Auction Coordination Status",
  "Privacy & Anonymization Audit",
];

export function CopilotDrawer({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "copilot",
      content:
        "**AURA Copilot Initialized.** I am ready to assist with real-time incident triage, sensor diagnostics, and coordination queries.",
      timestamp: new Date().toLocaleTimeString(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (textToSend?: string) => {
    const query = textToSend || input.trim();
    if (!query || loading) return;

    const userMsg: ChatMessage = {
      role: "user",
      content: query,
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/copilot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: query }),
      });
      const data = await res.json();

      const copilotMsg: ChatMessage = {
        role: "copilot",
        content: data.reply || "No response received.",
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, copilotMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "copilot",
          content: "⚠️ Failed to connect to copilot reasoning engine.",
          timestamp: new Date().toLocaleTimeString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, x: 380 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 380 }}
          transition={{ duration: 0.3, ease: "easeInOut" }}
          className="fixed top-0 right-0 h-full w-[380px] z-50 p-3 flex flex-col bg-[var(--bg-void)]/95 backdrop-blur-xl border-l border-[var(--border-secondary)] shadow-2xl"
        >
          <div className="flex items-center justify-between px-3 py-2.5 border-b border-[var(--border-secondary)] shrink-0">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-md bg-[var(--gold-glow)] border border-[var(--gold-primary)] flex items-center justify-center">
                <Bot className="w-3.5 h-3.5 text-[var(--gold-primary)]" />
              </div>
              <div>
                <div className="hud-text text-[12px] text-[var(--text-heading)] flex items-center gap-1.5">
                  AURA-Copilot
                  <span className="text-[9px] px-1 py-0.2 rounded bg-[var(--cyan-glow)] text-[var(--cyan-primary)] border border-[var(--cyan-primary)]/40 font-mono">
                    AI AGENT
                  </span>
                </div>
                <HudLabel>Operator Tactical Terminal</HudLabel>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)] transition"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Quick Prompt Chips */}
          <div className="flex flex-wrap gap-1.5 p-2 border-b border-[var(--border-secondary)] shrink-0 bg-[var(--bg-card)]/50">
            {QUICK_PROMPTS.map((p) => (
              <button
                key={p}
                disabled={loading}
                onClick={() => handleSend(p)}
                className="text-[10px] px-2 py-1 rounded border border-[var(--border-secondary)] bg-[var(--bg-void)] hover:border-[var(--gold-primary)] text-[var(--text-secondary)] hover:text-[var(--gold-primary)] transition"
              >
                {p}
              </button>
            ))}
          </div>

          {/* Message Stream */}
          <div className="flex-1 overflow-y-auto styled-scrollbar p-3 flex flex-col gap-3">
            {messages.map((m, idx) => (
              <div
                key={idx}
                className={`flex flex-col gap-1 ${m.role === "user" ? "items-end" : "items-start"}`}
              >
                <div className="flex items-center gap-1.5 text-[9px] text-[var(--text-secondary)] font-mono">
                  {m.role === "copilot" ? (
                    <>
                      <Sparkles className="w-2.5 h-2.5 text-[var(--gold-primary)]" />
                      <span>Copilot</span>
                    </>
                  ) : (
                    <span>Operator</span>
                  )}
                  <span>• {m.timestamp}</span>
                </div>
                <div
                  className={`p-2.5 rounded-lg text-[12px] leading-relaxed max-w-[92%] ${
                    m.role === "user"
                      ? "bg-[var(--gold-glow)] text-[var(--text-primary)] border border-[var(--gold-primary)]/40"
                      : "bg-[var(--bg-card)] text-[var(--text-primary)] border border-[var(--border-secondary)] font-[family-name:var(--font-body)]"
                  }`}
                >
                  <div className="whitespace-pre-wrap">{m.content}</div>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex items-center gap-2 text-[11px] text-[var(--gold-primary)] font-mono p-2 animate-pulse">
                <Terminal className="w-3.5 h-3.5" />
                Copilot analyzing surveillance state…
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Bar */}
          <div className="p-2 border-t border-[var(--border-secondary)] shrink-0 flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Ask copilot about site, alerts, sensors..."
              className="flex-1 bg-[var(--bg-card)] border border-[var(--border-secondary)] rounded-md px-3 py-2 text-[12px] text-[var(--text-primary)] placeholder-[var(--text-secondary)] focus:outline-none focus:border-[var(--gold-primary)] font-mono"
            />
            <button
              disabled={loading || !input.trim()}
              onClick={() => handleSend()}
              className="px-3 rounded-md bg-[var(--gold-primary)] hover:bg-[var(--gold-primary)]/90 text-black font-semibold disabled:opacity-40 flex items-center justify-center transition"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
