import { routeColor } from "@/lib/routes";
import type { RouteKey } from "@/lib/types";

const BRANCHES: RouteKey[] = ["answer", "action", "escalate", "spam"];

/**
 * The triage pipeline, made visible: ingest -> router -> one of four outcomes.
 * `active` lights the chosen branch in its route color; `processing` pulses the
 * router while a decision is in flight.
 */
export function PipelineRail({
  active,
  processing,
}: {
  active: RouteKey | null;
  processing: boolean;
}) {
  const litBranch = active;

  return (
    <div className="flex flex-col items-center gap-3 font-mono text-[11px] uppercase tracking-[0.18em] text-faint sm:flex-row sm:justify-center">
      <Stage label="ingest" lit={processing || active !== null} />
      <Connector lit={processing || active !== null} />
      <Stage
        label="router"
        lit={processing || active !== null}
        pulsing={processing}
        color="var(--color-brand)"
      />
      <Connector lit={active !== null} />
      <div className="flex items-center gap-2">
        {BRANCHES.map((b) => {
          const lit = litBranch === b;
          const c = routeColor(b);
          return (
            <span
              key={b}
              className="rounded-md px-2.5 py-1 transition-colors duration-500"
              style={{
                color: lit ? c : undefined,
                background: lit ? `color-mix(in oklab, ${c} 14%, transparent)` : "transparent",
                boxShadow: lit
                  ? `inset 0 0 0 1px color-mix(in oklab, ${c} 45%, transparent)`
                  : "inset 0 0 0 1px var(--color-edge)",
              }}
            >
              {b}
            </span>
          );
        })}
      </div>
    </div>
  );
}

function Stage({
  label,
  lit,
  pulsing,
  color = "var(--color-dim)",
}: {
  label: string;
  lit: boolean;
  pulsing?: boolean;
  color?: string;
}) {
  return (
    <span
      className="rounded-md px-2.5 py-1 transition-colors duration-500"
      style={{
        color: lit ? color : undefined,
        boxShadow: `inset 0 0 0 1px ${
          lit ? `color-mix(in oklab, ${color} 45%, transparent)` : "var(--color-edge)"
        }`,
        animation: pulsing ? "fade 0.9s ease-in-out infinite alternate" : "none",
      }}
    >
      {label}
    </span>
  );
}

function Connector({ lit }: { lit: boolean }) {
  return (
    <span
      className="h-px w-6 transition-colors duration-500 max-sm:h-4 max-sm:w-px"
      style={{
        background: lit ? "var(--color-brand)" : "var(--color-edge)",
      }}
    />
  );
}
