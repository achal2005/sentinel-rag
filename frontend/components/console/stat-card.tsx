import type { UsageStat } from "@/lib/types";

const TONE: Record<string, string> = {
  neutral: "var(--color-fg)",
  brand: "var(--color-brand)",
  answer: "var(--color-answer)",
  action: "var(--color-action)",
  escalate: "var(--color-escalate)",
  spam: "var(--color-spam)",
};

export function StatCard({ stat }: { stat: UsageStat }) {
  const color = TONE[stat.tone ?? "neutral"];
  const display = stat.value.toLocaleString(undefined, {
    minimumFractionDigits: stat.decimals ?? 0,
    maximumFractionDigits: stat.decimals ?? 0,
  });

  return (
    <div className="clay-hover rounded-2xl clay bg-surface p-4">
      <div className="flex items-start justify-between gap-2">
        <p className="eyebrow">{stat.label}</p>
        {stat.trend !== undefined && <TrendChip trend={stat.trend} />}
      </div>
      <p className="mt-3 font-display text-3xl font-semibold tabular-nums tracking-tight" style={{ color }}>
        {stat.prefix}
        {display}
        {stat.suffix}
      </p>
      <p className="mt-1 text-xs text-faint">{stat.hint}</p>
    </div>
  );
}

function TrendChip({ trend }: { trend: number }) {
  const up = trend >= 0;
  const color = up ? "var(--color-answer)" : "var(--color-escalate)";
  return (
    <span className="inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 font-mono text-[10px] font-medium" style={{ color, background: `color-mix(in oklab, ${color} 12%, transparent)` }}>
      <span aria-hidden>{up ? "↗" : "↘"}</span>
      {up ? "+" : ""}{trend}%
    </span>
  );
}
