"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { fetchRun } from "@/lib/api";
import type { InboxStatus, RunDetail, RunAuditStep } from "@/lib/types";
import { ago } from "@/lib/format";
import { ChannelIcon, channelLabel } from "@/components/console/channel-icon";
import { StatusBadge } from "@/components/console/status-badge";

const STEP_META: Record<string, { label: string; cssVar: string }> = {
  router: { label: "Router", cssVar: "--color-brand" },
  retrieve: { label: "Retrieval", cssVar: "--color-answer" },
  retrieval: { label: "Retrieval", cssVar: "--color-answer" },
  generation: { label: "Generation", cssVar: "--color-brand" },
  tool: { label: "Tool call", cssVar: "--color-action" },
  tool_call: { label: "Tool call", cssVar: "--color-action" },
  outcome: { label: "Outcome", cssVar: "--color-spam" },
  approval: { label: "Approval", cssVar: "--color-action" },
};

function statusOf(r: RunDetail): InboxStatus {
  if (r.route === "spam") return "spam";
  if (r.escalated || r.route === "escalate") return "escalated";
  if (r.route === "action") return "action_needed";
  return "answered";
}

export default function RequestTracePage() {
  const params = useParams<{ id: string }>();
  const id = params?.id;
  const [run, setRun] = useState<RunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    let alive = true;
    (async () => {
      try {
        const data = await fetchRun(id);
        if (alive) setRun(data);
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : "Failed to load trace.");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [id]);

  return (
    <div className="mx-auto w-full max-w-6xl px-5 py-10 sm:px-8 sm:py-12">
      <div className="max-w-4xl">
        <Link
          href="/inbox"
          className="inline-flex items-center gap-1.5 font-mono text-xs text-dim transition hover:text-fg"
        >
          <span aria-hidden>←</span> Inbox
        </Link>

        {loading ? (
          <TraceSkeleton />
        ) : error ? (
          <div className="mt-6 rounded-2xl clay bg-surface p-5 text-sm">
            <p className="font-medium text-escalate">{error}</p>
            <p className="mt-1 font-mono text-xs text-dim">
              Start the API: <span className="text-fg">uvicorn app.main:app --port 8000</span>
            </p>
          </div>
        ) : run ? (
          <Trace run={run} />
        ) : null}
      </div>
    </div>
  );
}

function TraceSkeleton() {
  return (
    <div aria-hidden>
      {/* header */}
      <div className="mt-5 flex items-start gap-3">
        <span className="clay-sm mt-0.5 grid size-10 shrink-0 place-items-center rounded-xl bg-surface">
          <div className="skeleton size-4.5 rounded" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="skeleton h-6 w-3/4 max-w-md" />
          <div className="mt-2.5 flex flex-wrap items-center gap-2">
            <div className="skeleton h-3 w-24" />
            <div className="skeleton h-3 w-16" />
            <div className="skeleton h-3 w-20" />
          </div>
        </div>
      </div>

      {/* outcome banner */}
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl clay-inset bg-surface-2/50 px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="skeleton h-6 w-24 rounded-full" />
          <div className="skeleton h-4 w-40" />
        </div>
        <div className="flex items-center gap-2">
          <div className="skeleton h-3 w-12" />
          <div className="skeleton h-3 w-10" />
          <div className="skeleton h-3 w-10" />
        </div>
      </div>

      {/* watch log — placeholder timeline nodes */}
      <section className="mt-8">
        <div className="skeleton mb-4 h-3 w-32" />
        <ol className="relative">
          {[0, 1, 2].map((i) => (
            <li key={i} className="relative grid grid-cols-[auto_1fr] gap-x-4 pb-6 last:pb-0">
              <div className="relative flex flex-col items-center">
                <span className="skeleton z-10 mt-1 size-3 rounded-full" />
                {i < 2 && <span className="w-px flex-1 bg-edge" aria-hidden />}
              </div>
              <div className="-mt-0.5 min-w-0">
                <div className="skeleton h-4 w-28" />
                <div className="mt-2 space-y-1.5">
                  <div className="skeleton h-3 w-56 max-w-full" />
                  <div className="skeleton h-3 w-40 max-w-full" />
                </div>
              </div>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}

function Trace({ run }: { run: RunDetail }) {
  const total = (run.latency_ms / 1000).toFixed(2);
  const cost = run.cost_usd === 0 ? "$0.00" : `$${run.cost_usd.toFixed(4)}`;
  const sender = run.sender ?? "web console";

  return (
    <>
      {/* header */}
      <div className="mt-5 flex items-start gap-3">
        <span
          className="clay-sm mt-0.5 grid size-10 shrink-0 place-items-center rounded-xl bg-surface text-dim"
          title={channelLabel(run.channel)}
        >
          <ChannelIcon channel={run.channel} className="size-4.5" />
        </span>
        <div className="min-w-0 flex-1">
          <h1 className="font-display text-xl font-semibold leading-snug tracking-tight text-fg sm:text-2xl">
            {run.request}
          </h1>
          <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 font-mono text-xs text-faint">
            <span className="text-dim">{sender}</span>
            <span className="text-edge-strong">·</span>
            <span>{channelLabel(run.channel)}</span>
            <span className="text-edge-strong">·</span>
            <span>{ago(run.created_at)}</span>
            <span className="text-edge-strong">·</span>
            <span>run #{run.id}</span>
          </p>
        </div>
      </div>

      {/* outcome banner */}
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl clay-inset bg-surface-2/50 px-4 py-3">
        <div className="flex items-center gap-3">
          <StatusBadge status={statusOf(run)} />
          {run.reason && <span className="text-sm text-dim">{run.reason}</span>}
          {run.action_status && (
            <span className="rounded-md bg-action/10 px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-action">
              {run.action_status.replaceAll("_", " ")}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 font-mono text-xs text-faint">
          <span className="text-answer">{cost}</span>
          <span className="text-edge-strong">·</span>
          <span>{run.total_tokens} tok</span>
          <span className="text-edge-strong">·</span>
          <span>{total}s</span>
        </div>
      </div>

      {/* the watch log — real audit steps */}
      {run.steps.length > 0 && (
        <section className="mt-8">
          <p className="eyebrow mb-4">Watch log · pipeline</p>
          <ol className="relative">
            {run.steps.map((step, i) => (
              <TraceNode key={i} step={step} index={i} last={i === run.steps.length - 1} model={run.model} />
            ))}
          </ol>
        </section>
      )}

      {/* citations */}
      {run.citations.length > 0 && (
        <section className="mt-8">
          <p className="eyebrow mb-3">Citations used</p>
          <div className="flex flex-wrap gap-2">
            {run.citations.map((c) => (
              <code
                key={c}
                className="rounded-lg px-2 py-1 font-mono text-xs"
                style={{
                  color: "var(--color-answer)",
                  background: "color-mix(in oklab, var(--color-answer) 12%, transparent)",
                }}
              >
                {c}
              </code>
            ))}
          </div>
        </section>
      )}
    </>
  );
}

// Keys we don't want to echo back as raw audit detail rows.
const SKIP = new Set(["queue_id", "ticket_id"]);

function TraceNode({
  step,
  index,
  last,
  model,
}: {
  step: RunAuditStep;
  index: number;
  last: boolean;
  model: string | null;
}) {
  const meta = STEP_META[step.step] ?? { label: step.step, cssVar: "--color-spam" };
  const c = `var(${meta.cssVar})`;
  const entries = Object.entries(step.detail ?? {}).filter(
    ([k, v]) => !SKIP.has(k) && v !== null && v !== "" && v !== undefined,
  );

  return (
    <li
      className="animate-rise relative grid grid-cols-[auto_1fr] gap-x-4 pb-6 last:pb-0"
      style={{ animationDelay: `${index * 60}ms` }}
    >
      <div className="relative flex flex-col items-center">
        <span
          className="z-10 mt-1 size-3 rounded-full"
          style={{ background: c, boxShadow: `0 0 0 4px color-mix(in oklab, ${c} 16%, transparent)` }}
        />
        {!last && <span className="w-px flex-1 bg-edge" aria-hidden />}
      </div>

      <div className="-mt-0.5 min-w-0">
        <div className="flex flex-wrap items-baseline gap-x-3">
          <span className="text-sm font-medium text-fg">{meta.label}</span>
          {step.step === "router" && model && (
            <span className="font-mono text-xs text-dim">{model}</span>
          )}
        </div>
        {entries.length > 0 && (
          <dl className="mt-1.5 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 font-mono text-xs">
            {entries.map(([k, v]) => (
              <div key={k} className="contents">
                <dt className="text-faint">{k}</dt>
                <dd className="min-w-0 break-words text-dim">
                  {typeof v === "object" ? JSON.stringify(v) : String(v)}
                </dd>
              </div>
            ))}
          </dl>
        )}
      </div>
    </li>
  );
}
