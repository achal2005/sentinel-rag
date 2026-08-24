"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { decideApproval, fetchApprovals } from "@/lib/api";
import type { ApprovalItem } from "@/lib/types";
import { ago } from "@/lib/format";
import { RiskBadge } from "@/components/console/risk-badge";
import { Button } from "@/components/ui/button";

type Notice = { kind: "ok" | "warn" | "err"; msg: string };

/** Turn a queued tool + params into a plain-language sentence for the operator.
 * Only the registered tools are named explicitly; anything else is described
 * generically so a newly added tool still reads sensibly. */
function describeAction(item: ApprovalItem): string {
  const p = item.params ?? {};
  const s = (k: string) => (p[k] == null ? undefined : String(p[k]));
  const email = s("requester_email") ?? s("email") ?? s("to");
  switch (item.tool) {
    case "cancel_invoice": {
      const inv = s("invoice_id") ?? s("invoice") ?? s("invoice_number");
      return `Cancel invoice ${inv ?? "on file"}`;
    }
    case "create_ticket":
      return `Open a support ticket${email ? ` for ${email}` : ""}`;
    default:
      return `Run ${item.tool}`;
  }
}

export default function ApprovalsPage() {
  const [items, setItems] = useState<ApprovalItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<Record<number, "approve" | "reject" | undefined>>({});
  const [notice, setNotice] = useState<Notice | null>(null);

  const load = useCallback(async () => {
    try {
      const rows = await fetchApprovals("pending");
      setItems(rows);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load the queue.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const first = window.setTimeout(load, 0);
    const t = setInterval(load, 10000);
    return () => {
      clearTimeout(first);
      clearInterval(t);
    };
  }, [load]);

  async function decide(item: ApprovalItem, action: "approve" | "reject") {
    setBusy((b) => ({ ...b, [item.id]: action }));
    setNotice(null);
    try {
      const res = await decideApproval(item.id, action);
      if (action === "reject") {
        setNotice({ kind: "ok", msg: `Rejected #${item.id} — ${item.tool} closed, tool not run.` });
      } else if (res.executed) {
        setNotice({ kind: "ok", msg: `Approved #${item.id} — ${item.tool} executed via n8n.` });
      } else {
        setNotice({
          kind: "warn",
          msg: `Approved #${item.id}, but the tool didn't run: ${res.error ?? "unknown error"}`,
        });
      }
      setItems((prev) => prev.filter((r) => r.id !== item.id));
    } catch (e) {
      setNotice({ kind: "err", msg: e instanceof Error ? e.message : "Action failed." });
      load();
    } finally {
      setBusy((b) => ({ ...b, [item.id]: undefined }));
    }
  }

  return (
    <div className="mx-auto w-full max-w-6xl px-5 py-10 sm:px-8 sm:py-12">
      <div className="max-w-4xl">
      {/* header */}
      <div>
        <p className="eyebrow text-action">Safety gate</p>
        <h1 className="mt-1.5 font-display text-2xl font-semibold tracking-tight text-fg sm:text-[28px]">
          Human decisions before side effects
        </h1>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-dim">
          High-risk tools stop here after parameter validation. Approving executes the
          registered n8n workflow; rejecting closes the request without the side effect.
        </p>
      </div>

      {/* action feedback */}
      {notice && (
        <div
          className="mt-6 rounded-xl p-3.5 text-sm text-fg"
          style={{
            background: `color-mix(in oklab, ${noticeColor(notice.kind)} 8%, transparent)`,
            boxShadow: `inset 0 0 0 1px color-mix(in oklab, ${noticeColor(notice.kind)} 32%, transparent)`,
          }}
        >
          {notice.msg}
        </div>
      )}

      {error && (
        <div
          className="mt-6 rounded-xl p-4 text-sm text-fg"
          style={{
            background: "color-mix(in oklab, var(--color-escalate) 8%, transparent)",
            boxShadow: "inset 0 0 0 1px color-mix(in oklab, var(--color-escalate) 35%, transparent)",
          }}
        >
          <p className="font-medium text-escalate">{error}</p>
          <p className="mt-1 font-mono text-xs text-dim">
            Start the API: <span className="text-fg">uvicorn app.main:app --port 8000</span>
          </p>
          <button onClick={load} className="mt-3 rounded-lg border border-edge bg-surface px-3 py-1.5 text-xs text-fg transition hover:border-edge-strong">
            Retry connection
          </button>
        </div>
      )}

      {/* queue */}
      <div className="mt-7 space-y-4">
        {loading && !items.length ? (
          <>
            <ApprovalCardSkeleton />
            <ApprovalCardSkeleton />
          </>
        ) : !error && items.length === 0 ? (
          <EmptyState />
        ) : (
          items.map((item) => (
            <ApprovalCard
              key={item.id}
              item={item}
              busy={busy[item.id]}
              onApprove={() => decide(item, "approve")}
              onReject={() => decide(item, "reject")}
            />
          ))
        )}
      </div>
      </div>
    </div>
  );
}

/** Placeholder that mirrors ApprovalCard's shape so the layout doesn't jump
 * when real items arrive. Obviously a placeholder — never fake pending data. */
function ApprovalCardSkeleton() {
  return (
    <div className="overflow-hidden rounded-2xl clay bg-surface" aria-hidden>
      <div className="h-0.5 w-full bg-edge" />
      <div className="space-y-4 p-5 sm:p-6">
        {/* header: risk-badge-sized block + short mono line, timestamp on the right */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <div className="skeleton h-5 w-16 rounded-full" />
          <div className="skeleton h-3.5 w-20" />
          <div className="skeleton ml-auto h-3 w-12" />
        </div>

        {/* proposed action */}
        <div className="space-y-2">
          <div className="skeleton h-3 w-24" />
          <div className="skeleton h-4 w-52" />
        </div>

        {/* footer: two button-sized blocks on the right */}
        <div className="flex items-center justify-between gap-3 pt-1">
          <div className="skeleton h-3 w-32" />
          <div className="flex items-center gap-2.5">
            <div className="skeleton h-7 w-16 rounded-[min(var(--radius-md),12px)]" />
            <div className="skeleton h-7 w-28 rounded-[min(var(--radius-md),12px)]" />
          </div>
        </div>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="rounded-2xl clay bg-surface px-6 py-16 text-center">
      <span
        className="mx-auto grid size-11 place-items-center rounded-xl text-answer"
        style={{ boxShadow: "inset 0 0 0 1px color-mix(in oklab, var(--color-answer) 30%, transparent)" }}
      >
        <svg className="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <path d="m20 6-11 11-5-5" />
        </svg>
      </span>
      <p className="mt-4 text-sm text-fg">All caught up — nothing needs your approval.</p>
      <p className="mt-1 font-mono text-xs text-faint">
        A quiet queue is the healthy state. High-risk actions from the console will surface here.
      </p>
      <Link href="/console" className="beacon-btn group mt-6">
        Open the live console
        <span className="transition-transform group-hover:translate-x-0.5" aria-hidden>→</span>
      </Link>
    </div>
  );
}

function noticeColor(kind: Notice["kind"]): string {
  return kind === "ok"
    ? "var(--color-answer)"
    : kind === "warn"
      ? "var(--color-action)"
      : "var(--color-escalate)";
}

const RISK_ACCENT: Record<string, string> = {
  high: "var(--color-escalate)",
  medium: "var(--color-action)",
  low: "var(--color-spam)",
};

function ApprovalCard({
  item,
  busy,
  onApprove,
  onReject,
}: {
  item: ApprovalItem;
  busy: "approve" | "reject" | undefined;
  onApprove: () => void;
  onReject: () => void;
}) {
  const c = RISK_ACCENT[item.risk_level] ?? "var(--color-spam)";
  const working = busy !== undefined;

  return (
    <article
      className="animate-rise overflow-hidden rounded-2xl clay bg-surface"
      style={{ boxShadow: `0 0 0 1px color-mix(in oklab, ${c} 18%, transparent)` }}
    >
      <div className="h-0.5 w-full" style={{ background: c }} />
      <div className="space-y-4 p-5 sm:p-6">
        {/* header */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <RiskBadge level={item.risk_level} />
          {item.run_id ? (
            <Link href={`/requests/${item.run_id}`} className="font-mono text-xs text-brand transition hover:text-fg">
              run #{item.run_id} ↗
            </Link>
          ) : (
            <span className="font-mono text-xs text-faint">approval #{item.id}</span>
          )}
          <span className="ml-auto font-mono text-[11px] text-faint">{ago(item.created_at)}</span>
        </div>

        {/* proposed action, in plain language */}
        <div>
          <p className="eyebrow mb-1.5">Proposed action</p>
          <p className="text-[15px] font-medium text-fg">{describeAction(item)}</p>
        </div>

        {/* reasoning */}
        {item.reason && (
          <p className="text-sm leading-relaxed text-dim">
            <span className="font-mono text-faint">why&nbsp;›&nbsp;</span>
            {item.reason}
          </p>
        )}

        {/* the exact parameters the tool would run with */}
        <details className="group clay-inset rounded-xl bg-surface-2/40">
          <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-2.5 font-mono text-[11px] uppercase tracking-[0.16em] text-faint transition hover:text-dim">
            Tool · {item.tool}
            <span className="transition group-open:rotate-180" aria-hidden>⌄</span>
          </summary>
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 border-t border-edge px-4 py-3 font-mono text-xs">
            {Object.entries(item.params ?? {}).map(([k, v]) => (
              <div key={k} className="contents">
                <dt className="text-faint">{k}</dt>
                <dd className="break-words text-dim">{String(v)}</dd>
              </div>
            ))}
          </dl>
        </details>

        {/* decision */}
        <div className="flex items-center justify-between gap-3 pt-1">
          <span className="font-mono text-[11px] text-faint">
            Held — not executed yet
          </span>
          <div className="flex items-center gap-2.5">
            <Button variant="destructive" size="sm" disabled={working} onClick={onReject}>
              {busy === "reject" ? "Rejecting…" : "Reject"}
            </Button>
            <Button size="sm" disabled={working} onClick={onApprove}>
              {busy === "approve" ? "Approving…" : "Approve & run"}
            </Button>
          </div>
        </div>
      </div>
    </article>
  );
}
