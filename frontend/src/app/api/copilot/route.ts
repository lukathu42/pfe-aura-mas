import { NextRequest, NextResponse } from "next/server";
import fs from "node:fs/promises";
import path from "node:path";
import { DATA_ROOT } from "@/lib/paths";
import type { Alert } from "@/lib/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

async function loadRecentAlerts(): Promise<Alert[]> {
  try {
    const files = (await fs.readdir(DATA_ROOT)).filter(
      (f) => f.startsWith("alerts_") && f.endsWith(".jsonl"),
    );
    const alerts: Alert[] = [];
    for (const file of files) {
      try {
        const raw = await fs.readFile(path.join(DATA_ROOT, file), "utf-8");
        for (const line of raw.split("\n")) {
          if (!line.trim()) continue;
          try {
            alerts.push(JSON.parse(line));
          } catch {}
        }
      } catch {}
    }
    alerts.sort((a, b) => b.timestamp - a.timestamp);
    return alerts.slice(0, 10);
  } catch {
    return [];
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => null);
    const message = (body?.message || "").trim();

    if (!message) {
      return NextResponse.json({ error: "Empty message" }, { status: 400 });
    }

    const recentAlerts = await loadRecentAlerts();
    const openAlerts = recentAlerts.filter((a) => a.status === "OPEN");
    const criticalAlerts = recentAlerts.filter((a) => a.severity === "CRITICAL");

    // Local heuristic answering engine with real database context
    const msg = message.toLowerCase();
    let responseText = "";

    if (msg.includes("status") || msg.includes("summary") || msg.includes("overview")) {
      responseText = `**Site Security Status Overview**:\n` +
        `• **Active Open Incidents**: ${openAlerts.length}\n` +
        `• **Critical Threats**: ${criticalAlerts.length}\n` +
        `• **Total Recent Alerts Logged**: ${recentAlerts.length}\n` +
        `• **Monitored Modalities**: Concurrent Video (YOLO11n + ByteTrack) & Audio (YAMNet 521-class).\n` +
        `• **Coordination State**: Sealed-bid verification auctions active across camera agents.`;
    } else if (msg.includes("alert") || msg.includes("incident") || msg.includes("intrusion") || msg.includes("threat")) {
      if (recentAlerts.length === 0) {
        responseText = "No active alerts currently recorded in the system audit stream.";
      } else {
        const top = recentAlerts[0];
        const composite = top.contributing_types?.join(" + ") || top.event_type;
        responseText = `**Latest Incident Details (${top.alert_id})**:\n` +
          `• **Type**: \`${composite.replace(/_/g, " ")}\`\n` +
          `• **Severity**: **${top.severity}** (Fused Confidence: ${(top.confidence * 100).toFixed(1)}%)\n` +
          `• **Zone**: ${top.zone ?? "Global Site"}\n` +
          `• **Status**: ${top.status}\n` +
          `• **Sensors Involved**: ${top.sensors.join(", ") || "None"}\n` +
          `• **Agentic Summary**: ${top.explanation || "Standard heuristic detection."}`;
      }
    } else if (msg.includes("coordination") || msg.includes("auction") || msg.includes("bandit")) {
      responseText = `**Coordination Subsystem Details**:\n` +
        `• **Protocol**: Single-round Contract-Net Protocol (CNP) with LinUCB Contextual Bandit mode.\n` +
        `• **Gray-Zone Threshold**: Hypotheses with confidence between \`0.35\` and \`0.75\` automatically trigger cross-sensor verification.\n` +
        `• **Reinforcement Learning**: Operator acknowledgment actions actively train camera selection weights in real-time.`;
    } else if (msg.includes("privacy") || msg.includes("anonymiz") || msg.includes("gdpr")) {
      responseText = `**Privacy-by-Design Governance**:\n` +
        `• **Raw Frame Retention**: Zero. Raw video never leaves edge nodes.\n` +
        `• **Anonymization**: Person bounding boxes and facial features are Gaussian-blurred at edge capture.\n` +
        `• **Audit Guarantee**: Every automated alert, suppression, and operator action is cryptographically timestamped in the audit stream.`;
    } else {
      responseText = `**AURA Copilot**: I have analyzed your request regarding *"**${message}**"*. ` +
        `There are currently **${openAlerts.length} open alert(s)** requiring operator attention. ` +
        `You can ask me to **summarize active incidents**, **explain coordinator decisions**, or **query zone statuses**.`;
    }

    return NextResponse.json({
      reply: responseText,
      timestamp: Date.now() / 1000,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal server error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
