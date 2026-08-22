"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Radio, Gavel, CheckCircle2, XCircle } from "lucide-react";
import { GlassPanel } from "./primitives/GlassPanel";
import { HudLabel } from "./primitives/Hud";
import { useAuraData } from "./DataProvider";
import type { CoordinationRound } from "@/lib/types";

function RoundCard({ round }: { round: CoordinationRound }) {
  const sortedBids = [...round.bids].sort((a, b) => b.bid - a.bid);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 24 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -24 }}
      transition={{ duration: 0.35, ease: [0.34, 1.56, 0.64, 1] }}
      className="glass-panel-sm flex flex-col gap-2 p-3"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Radio className="w-3 h-3 text-[var(--cyan-primary)]" />
          <span className="hud-text text-[10px] text-[var(--text-primary)]">
            {round.task.event_type.replace(/_/g, " ")}
          </span>
        </div>
        <HudLabel>{round.task.zone ?? "site"}</HudLabel>
      </div>
      <HudLabel>ORIGIN {round.task.origin_sensor}</HudLabel>

      {/* Bids stream in */}
      <div className="flex flex-wrap gap-1.5">
        <AnimatePresence>
          {sortedBids.map((bid) => (
            <motion.span
              key={bid.agent_id}
              layout
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              className={`hud-text text-[9px] px-1.5 py-0.5 rounded border ${
                round.award?.winner === bid.agent_id
                  ? "border-[var(--gold-primary)] text-[var(--gold-primary)] bg-[var(--gold-glow)]"
                  : "border-[var(--border-secondary)] text-[var(--text-secondary)]"
              }`}
            >
              {bid.agent_id} {bid.bid.toFixed(2)}
            </motion.span>
          ))}
        </AnimatePresence>
        {sortedBids.length === 0 && <span className="hud-label">awaiting bids…</span>}
      </div>

      {/* Award */}
      {round.award && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center gap-1.5 pt-1 border-t border-[var(--border-secondary)]"
        >
          <Gavel className="w-3 h-3 text-[var(--gold-primary)]" />
          <span className="hud-text text-[9px] text-[var(--gold-primary)]">
            AWARDED → {round.award.winner}
          </span>
        </motion.div>
      )}

      {/* Verification outcome */}
      {round.verification && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-1.5"
        >
          {round.verification.verified ? (
            <CheckCircle2 className="w-3 h-3 text-[var(--sev-resolved)]" />
          ) : (
            <XCircle className="w-3 h-3 text-[var(--sev-critical)]" />
          )}
          <span
            className={`hud-text text-[9px] ${
              round.verification.verified
                ? "text-[var(--sev-resolved)]"
                : "text-[var(--sev-critical)]"
            }`}
          >
            {round.verification.verified ? "VERIFIED" : "NOT VERIFIED"} ·{" "}
            {round.verification.verification_score.toFixed(2)}
          </span>
        </motion.div>
      )}
    </motion.div>
  );
}

/** Signature element: a live readout of AURA-MAS's own auction-based
 * coordination protocol (site/coordination/{tasks,bids,awards,
 * verifications}) — nothing in OSIRIS has an analog to this, it's the
 * thesis's actual novel mechanism, so this is the one place worth real
 * motion budget. */
export function CoordinationConsole() {
  const { rounds } = useAuraData();

  return (
    <GlassPanel className="flex flex-col overflow-hidden h-full">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-[var(--border-secondary)]">
        <Gavel className="w-3.5 h-3.5 text-[var(--gold-primary)]" />
        <span className="hud-text text-[11px] text-[var(--text-primary)]">Coordination Console</span>
        <HudLabel>Auction protocol, live</HudLabel>
      </div>
      <div className="flex-1 overflow-y-auto styled-scrollbar p-2 flex flex-col gap-2">
        {rounds.length === 0 && (
          <span className="hud-label px-2 py-3">
            No verification tasks yet — auctions fire when FusionAgent confidence lands in
            the gray zone.
          </span>
        )}
        <AnimatePresence mode="popLayout">
          {rounds.map((round) => (
            <RoundCard key={round.task.task_id} round={round} />
          ))}
        </AnimatePresence>
      </div>
    </GlassPanel>
  );
}
