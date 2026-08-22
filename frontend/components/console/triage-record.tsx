import { Fragment } from "react";
import Link from "next/link";
import { ROUTES, routeColor } from "@/lib/routes";
import type { TriageRecord } from "@/lib/types";
import { RouteBadge } from "./route-badge";
import { EvidenceList } from "./evidence-list";

/** Render answer text with [citation-id] tokens turned into inline pills. */
function AnswerText({ text }: { text: string }) {
  const citation = /\[([a-z]+-\d+)\]/g;
  const parts: React.ReactNode[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  let k = 0;
  while ((m = citation.exec(text)) !== null) {
    if (m.index > last) parts.push(<Fragment key={k++}>{text.slice(last, m.index)}</Fragment>);
    parts.push(
      <code
        key={k++}
        className="mx-0.5 rounded px-1 py-0.5 font-mono text-[0.8em]"
        style={{
          color: "var(--color-answer)",
          background: "color-mix(in oklab, var(--color-answer) 12%, transparent)",
        }}
      >
        {m[1]}
      </code>,
    );
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push(<Fragment key={k++}>{text.slice(last)}</Fragment>);
  return <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-fg">{parts}</p>;
}

const urgencyColor = (u: string) =>
  u === "high" ? "var(--color-escalate)" : u === "medium" ? "var(--color-action)" : "var(--color-dim)";

export function TriageRecordCard({ record }: { record: TriageRecord }) {
  // The answer path can self-escalate (e.g. it couldn't ground a citation), so
  // the badge must reflect the FINAL decision, not just the router's route.
  const displayRoute = record.escalated ? "escalate" : record.route;
  const c = routeColor(displayRoute);
  const meta = ROUTES[displayRoute];

  return (
    <article
      className="animate-rise overflow-hidden rounded-2xl bg-surface"
      style={{
        boxShadow: `inset 0 0 0 1px var(--color-edge), 0 0 0 1px color-mix(in oklab, ${c} 22%, transparent), 0 24px 60px -30px color-mix(in oklab, ${c} 40%, transparent)`,
      }}
    >
      {/* route-colored top edge */}
      <div className="h-0.5 w-full" style={{ background: c }} />

      <div className="space-y-5 p-5 sm:p-6">
        {/* the request */}
        <p className="text-sm text-dim">
          <span className="font-mono text-faint">request&nbsp;›&nbsp;</span>
          {record.query}
        </p>

        {/* decision header */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <RouteBadge route={displayRoute} />
          <Meta label="urgency" value={record.urgency} color={urgencyColor(record.urgency)} />
          <Meta label="intent" value={record.intent} />
          <Meta label="reason" value={record.reason} />
          <span className="ml-auto flex items-center gap-2 font-mono text-xs text-faint">
            <span>{record.total_tokens.toLocaleString()} tok</span>
            <span className="text-edge-strong">·</span>
            <span>{record.latency_ms.toLocaleString()} ms</span>
            <span className="text-edge-strong">·</span>
            <span>{record.cost_usd === 0 ? "$0.00" : `$${record.cost_usd.toFixed(4)}`}</span>
          </span>
        </div>

        <p className="text-sm text-dim">{meta.blurb}</p>

        <div className="h-px w-full bg-edge" />

        {/* outcome body */}
        <AnswerText text={record.answer} />

        {/* action: the planned side effect awaiting approval */}
        {record.action && (
          <div
            className="rounded-xl p-4"
            style={{
              background: "color-mix(in oklab, var(--color-action) 8%, transparent)",
              boxShadow: "inset 0 0 0 1px color-mix(in oklab, var(--color-action) 30%, transparent)",
            }}
          >
            <div className="mb-2 flex items-center justify-between">
              <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-action">
                Planned action
              </span>
              <Link
                href="/approvals"
                title="Review high-risk actions in the approval queue"
                className="rounded-md px-2.5 py-1 font-mono text-[11px] text-action transition-colors hover:text-fg"
                style={{ boxShadow: "inset 0 0 0 1px color-mix(in oklab, var(--color-action) 40%, transparent)" }}
              >
                Review in queue →
              </Link>
            </div>
            <pre className="overflow-x-auto font-mono text-xs leading-relaxed text-dim">
              {JSON.stringify(record.action, null, 2)}
            </pre>
          </div>
        )}

        {/* evidence */}
        {record.sources.length > 0 && (
          <>
            <div className="h-px w-full bg-edge" />
            <EvidenceList sources={record.sources} confidenceMin={record.confidence_min} />
          </>
        )}

        {record.run_id && (
          <div className="flex justify-end border-t border-edge pt-4">
            <Link href={`/requests/${record.run_id}`} className="font-mono text-xs text-brand transition hover:text-fg">
              Open persisted trace · run #{record.run_id} →
            </Link>
          </div>
        )}
      </div>
    </article>
  );
}

function Meta({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <span className="inline-flex items-baseline gap-1.5 font-mono text-xs">
      <span className="text-faint">{label}</span>
      <span style={{ color: color ?? "var(--color-fg)" }}>{value}</span>
    </span>
  );
}
