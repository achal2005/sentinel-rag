"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchRuns } from "@/lib/api";
import type { InboxStatus, RunRow } from "@/lib/types";
import { ago } from "@/lib/format";
import { ChannelIcon, channelLabel } from "@/components/console/channel-icon";
import { StatusBadge, statusLabel } from "@/components/console/status-badge";

type Filter = "all" | InboxStatus;

const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "action_needed", label: "Action needed" },
  { key: "escalated", label: "Escalated" },
  { key: "answered", label: "Answered" },
  { key: "spam", label: "Spam" },
];

// Derive the operator-facing status from the run's route + escalation flag.
function toStatus(r: RunRow): InboxStatus {
  if (r.route === "spam") return "spam";
  if (r.escalated || r.route === "escalate") return "escalated";
  if (r.route === "action") return "action_needed";
  return "answered";
}

export default function InboxPage() {
  const [runs, setRuns] = useState<RunRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("all");

  const load = useCallback(async () => {
    try {
      const rows = await fetchRuns(40);
      setRuns(rows);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load the inbox.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const first = window.setTimeout(load, 0);
    const t = setInterval(load, 12000); // keep the inbox fresh
    return () => {
      clearTimeout(first);
      clearInterval(t);
    };
  }, [load]);

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: runs.length };
    for (const r of runs) {
      const s = toStatus(r);
      c[s] = (c[s] ?? 0) + 1;
    }
    return c;
  }, [runs]);

  const rows = useMemo(
    () => (filter === "all" ? runs : runs.filter((r) => toStatus(r) === filter)),
    [runs, filter],
  );

  return (
    <div className="mx-auto w-full max-w-6xl px-5 py-10 sm:px-8 sm:py-12">
      {/* header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow text-brand">Run log</p>
          <h1 className="mt-1.5 font-display text-2xl font-semibold tracking-tight text-fg sm:text-[28px]">
            Every handled request
          </h1>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-dim">
            Live records from the backend, newest first. Open any request to inspect
            its route, cost, citations and audit trail.
          </p>
        </div>
        <span className="font-mono text-xs text-faint">
          {counts.all} handled · live
        </span>
      </div>

      {/* filters */}
      <div className="mt-6 flex flex-wrap items-center gap-2">
        {FILTERS.map((f) => {
          const n = counts[f.key] ?? 0;
          const active = filter === f.key;
          return (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              aria-pressed={active}
              className={`clay-sm inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm transition ${
                active ? "bg-surface-2 text-fg" : "bg-surface text-dim hover:text-fg"
              }`}
            >
              {f.label}
              <span className="font-mono text-[11px] text-faint">{n}</span>
            </button>
          );
        })}
      </div>

      {/* list */}
      <div className="mt-5 overflow-hidden rounded-2xl clay bg-surface">
        {error ? (
          <Offline message={error} onRetry={load} />
        ) : loading ? (
          <p className="px-6 py-16 text-center font-mono text-xs text-faint">Loading inbox…</p>
        ) : rows.length === 0 ? (
          <div className="px-6 py-16 text-center">
            <p className="text-sm text-dim">
              {runs.length === 0 ? "No requests yet." : "Nothing here right now."}
            </p>
            <p className="mt-1 font-mono text-xs text-faint">
              {runs.length === 0
                ? "Run one through the console and it'll appear here."
                : `No ${statusLabel(filter as InboxStatus).toLowerCase()} requests.`}
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-edge/60">
            {rows.map((r, i) => (
              <InboxRow key={r.id} run={r} index={i} />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function Offline({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="px-6 py-14 text-center">
      <span className="mx-auto grid size-10 place-items-center rounded-full bg-escalate/10 text-escalate" aria-hidden>
        !
      </span>
      <p className="mt-3 text-sm font-medium text-escalate">{message}</p>
      <p className="mt-2 font-mono text-xs text-dim">
        Start the API: <span className="text-fg">uvicorn app.main:app --port 8000</span>
      </p>
      <button onClick={onRetry} className="mt-4 rounded-lg border border-edge bg-surface-2 px-3 py-1.5 text-xs text-fg transition hover:border-edge-strong">
        Retry connection
      </button>
    </div>
  );
}

function InboxRow({ run, index }: { run: RunRow; index: number }) {
  const status = toStatus(run);
  const sender = run.sender ?? "web console";
  return (
    <li className="animate-rise" style={{ animationDelay: `${Math.min(index * 30, 300)}ms` }}>
      <Link
        href={`/requests/${run.id}`}
        className="group grid grid-cols-[auto_1fr_auto] items-center gap-4 px-4 py-3.5 transition hover:bg-surface-2/50 sm:px-5"
      >
        <span
          className="clay-sm grid size-9 place-items-center rounded-xl bg-surface text-dim transition group-hover:text-fg"
          title={channelLabel(run.channel)}
        >
          <ChannelIcon channel={run.channel} />
        </span>

        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="truncate text-sm font-medium text-fg">{sender}</span>
            <span className="hidden font-mono text-[11px] text-faint sm:inline">
              {channelLabel(run.channel)}
            </span>
          </div>
          <p className="mt-0.5 truncate text-sm text-dim">{run.request}</p>
        </div>

        <div className="flex flex-col items-end gap-1.5">
          <StatusBadge status={status} />
          <div className="flex items-center gap-2 font-mono text-[11px] text-faint">
            {run.model && <span className="hidden sm:inline">{run.model}</span>}
            {run.model && <span className="hidden text-edge-strong sm:inline">·</span>}
            <span>{ago(run.created_at)}</span>
          </div>
        </div>
      </Link>
    </li>
  );
}
