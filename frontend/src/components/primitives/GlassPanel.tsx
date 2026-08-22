import type { ReactNode } from "react";

export function GlassPanel({
  children,
  interactive = false,
  className = "",
}: {
  children: ReactNode;
  interactive?: boolean;
  className?: string;
}) {
  return (
    <div
      className={`${interactive ? "glass-panel-interactive" : "glass-panel"} ${className}`}
    >
      {children}
    </div>
  );
}

export function PulseRing({
  variant = "gold",
  size = 8,
}: {
  variant?: "gold" | "cyan" | "critical";
  size?: number;
}) {
  const dotColor =
    variant === "cyan"
      ? "bg-[var(--cyan-primary)]"
      : variant === "critical"
        ? "bg-[var(--sev-critical)]"
        : "bg-[var(--gold-primary)]";
  const ringClass =
    variant === "cyan"
      ? "pulse-ring--cyan"
      : variant === "critical"
        ? "pulse-ring--critical"
        : "";
  return (
    <span
      className={`pulse-ring ${ringClass}`}
      style={{ width: size, height: size }}
    >
      <span className={`rounded-full ${dotColor}`} style={{ width: size, height: size }} />
    </span>
  );
}

export function TacticalButton({
  children,
  onClick,
  variant = "gold",
  disabled = false,
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "gold" | "cyan";
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`btn-tactical ${variant === "cyan" ? "btn-tactical--cyan" : ""} disabled:opacity-40 disabled:cursor-not-allowed`}
    >
      {children}
    </button>
  );
}
