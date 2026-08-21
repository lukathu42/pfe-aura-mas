import type { Severity } from "@/lib/types";

const VARIANT: Record<Severity, string> = {
  CRITICAL: "severity-tag--critical",
  WARNING: "severity-tag--warning",
  INFO: "severity-tag--info",
};

export function SeverityTag({ severity }: { severity: Severity }) {
  return <span className={`severity-tag ${VARIANT[severity]}`}>{severity}</span>;
}

export function StatusTag({ status }: { status: "OPEN" | "ACKNOWLEDGED" | "DISMISSED" }) {
  if (status === "OPEN") return <span className="severity-tag severity-tag--critical">OPEN</span>;
  if (status === "ACKNOWLEDGED")
    return <span className="severity-tag severity-tag--system">ACKNOWLEDGED</span>;
  return <span className="severity-tag severity-tag--resolved">DISMISSED</span>;
}
