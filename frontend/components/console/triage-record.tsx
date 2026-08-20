import { Fragment } from "react";
import { ROUTES, routeColor } from "@/lib/routes";
import type { TriageRecord } from "@/lib/types";
import { RouteBadge } from "./route-badge";
import { EvidenceList } from "./evidence-list";

const CITATION = /\[([a-z]+-\d+)\]/g;

/** Render answer text with [citation-id] tokens turned into inline pills. */
function AnswerText({ text }: { text: string }) {
  const parts: React.ReactNode[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  CITATION.lastIndex = 0;
  let k = 0;
  while ((m = CITATION.exec(text)) !== null) {
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
  const c = routeColor(record.route);
  const meta = ROUTES[record.route];

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
          <RouteBadge route={record.route} />
          <Meta label="urgency" value={record.urgency} color={urgencyColor(record.urgency)} />
          <Meta label="intent" value={record.intent} />
          <Meta label="reason" value={record.reason} />
          <span className="ml-auto font-mono text-xs text-faint">{record.latency_ms} ms</span>
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
              <button
                disabled
                title="Approval queue arrives in Week 3"
                className="cursor-not-allowed rounded-md px-2.5 py-1 font-mono text-[11px] text-faint"
                style={{ boxShadow: "inset 0 0 0 1px var(--color-edge)" }}
              >
                Approve — Week 3
              </button>
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
            <EvidenceList sources={record.sources} />
          </>
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
