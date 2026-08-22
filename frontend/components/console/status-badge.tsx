import type { InboxStatus } from "@/lib/types";

// Status is the one thing color must encode consistently across the console:
// green = resolved, amber = needs an action, red = escalated, gray = spam.
const META: Record<InboxStatus, { label: string; cssVar: string }> = {
  answered: { label: "Answered", cssVar: "--color-answer" },
  action_needed: { label: "Action needed", cssVar: "--color-action" },
  escalated: { label: "Escalated", cssVar: "--color-escalate" },
  spam: { label: "Spam", cssVar: "--color-spam" },
};

export function StatusBadge({ status }: { status: InboxStatus }) {
  const { label, cssVar } = META[status];
  const c = `var(${cssVar})`;
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium"
      style={{
        color: c,
        background: `color-mix(in oklab, ${c} 11%, transparent)`,
        boxShadow: `inset 0 0 0 1px color-mix(in oklab, ${c} 32%, transparent)`,
      }}
    >
      <span className="size-1.5 rounded-full" style={{ background: c, boxShadow: `0 0 7px ${c}` }} />
      {label}
    </span>
  );
}

export function statusLabel(status: InboxStatus): string {
  return META[status].label;
}
