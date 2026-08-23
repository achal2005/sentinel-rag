import type { RiskLevel } from "@/lib/types";

// Risk maps onto the same semantic palette as routes: high = escalate (red),
// medium = action (amber), low = spam-grey. Color is the signal here too.
const RISK_COLOR: Record<RiskLevel, string> = {
  high: "var(--color-escalate)",
  medium: "var(--color-action)",
  low: "var(--color-spam)",
};

export function RiskBadge({ level }: { level: RiskLevel }) {
  const c = RISK_COLOR[level] ?? "var(--color-spam)";
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider"
      style={{
        color: c,
        background: `color-mix(in oklab, ${c} 12%, transparent)`,
        boxShadow: `inset 0 0 0 1px color-mix(in oklab, ${c} 35%, transparent)`,
      }}
    >
      <span className="size-1.5 rounded-full" style={{ background: c, boxShadow: `0 0 8px ${c}` }} />
      {level} risk
    </span>
  );
}
