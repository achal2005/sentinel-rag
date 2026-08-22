import type { Source } from "@/lib/types";

/**
 * Retrieved chunks with similarity bars — the confidence gate made visible.
 * The dashed marker sits at the escalation threshold, so you can see why a
 * request was grounded or handed off.
 */
export function EvidenceList({ sources, confidenceMin }: { sources: Source[]; confidenceMin: number }) {
  if (sources.length === 0) return null;
  return (
    <div className="space-y-2.5">
      <div className="flex items-center justify-between font-mono text-[11px] uppercase tracking-[0.18em] text-faint">
        <span>Evidence · retrieved chunks</span>
        <span>gate ≥ {confidenceMin.toFixed(2)}</span>
      </div>
      <ul className="space-y-2">
        {sources.map((s, i) => {
          const passes = s.similarity >= confidenceMin;
          const c = passes ? "var(--color-answer)" : "var(--color-faint)";
          return (
            <li key={i} className="grid grid-cols-[auto_1fr_auto] items-center gap-3">
              <code
                className="rounded px-1.5 py-0.5 font-mono text-xs"
                style={{
                  color: c,
                  background: `color-mix(in oklab, ${c} 12%, transparent)`,
                }}
              >
                {s.citation_id ?? "no-id"}
              </code>
              <div className="min-w-0">
                <p className="truncate text-sm text-fg">{s.heading}</p>
                <p className="truncate font-mono text-[11px] text-faint">{s.doc}</p>
              </div>
              <div className="flex items-center gap-2">
                <div className="relative h-1.5 w-20 overflow-hidden rounded-full bg-surface-2 sm:w-28">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${Math.round(s.similarity * 100)}%`,
                      background: c,
                    }}
                  />
                  <div
                    className="absolute inset-y-0 w-px bg-edge-strong"
                    style={{ left: `${confidenceMin * 100}%` }}
                  />
                </div>
                <span className="w-9 text-right font-mono text-xs text-dim">
                  {s.similarity.toFixed(2)}
                </span>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
