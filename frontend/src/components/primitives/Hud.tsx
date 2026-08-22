export function HudLabel({ children }: { children: React.ReactNode }) {
  return <span className="hud-label">{children}</span>;
}

export function HudValue({ children }: { children: React.ReactNode }) {
  return <span className="hud-value">{children}</span>;
}

export function HudRow({
  label,
  value,
}: {
  label: React.ReactNode;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <HudLabel>{label}</HudLabel>
      <HudValue>{value}</HudValue>
    </div>
  );
}
