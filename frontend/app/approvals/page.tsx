"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { decideApproval, fetchApprovals } from "@/lib/api";
import type { ApprovalItem, RiskLevel } from "@/lib/types";
import { SystemStatus } from "@/components/console/system-status";
import { RiskBadge } from "@/components/console/risk-badge";
import { Button } from "@/components/ui/button";

const RISK_COLOR: Record<RiskLevel, string> = {
  high: "var(--color-escalate)",
  medium: "var(--color-action)",
  low: "var(--color-spam)",
};

type Notice = { kind: "ok" | "warn" | "err"; msg: string };

function ago(iso: string): string {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return `${Math.floor(s)}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
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
    load();
    const t = setInterval(load, 10000); // keep the queue fresh
    return () => clearInterval(t);
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
        // Approved, but the webhook didn't complete (e.g. workflow not set up).
        setNotice({
          kind: "warn",
          msg: `Approved #${item.id}, but the tool didn't run: ${res.error ?? "unknown error"}`,
        });
      }
      // It's no longer pending — drop it from the list.
      setItems((prev) => prev.filter((r) => r.id !== item.id));
    } catch (e) {
      setNotice({ kind: "err", msg: e instanceof Error ? e.message : "Action failed." });
      load(); // resync in case state drifted
    } finally {
      setBusy((b) => ({ ...b, [item.id]: undefined }));
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-5 pb-24">
      {/* top bar */}
      <header className="flex items-center justify-between py-6">
        <div className="flex items-center gap-2.5">
          <Link href="/" className="font-display text-lg font-semibold tracking-tight text-fg">
            Sentinel
          </Link>
          <span className="hidden font-mono text-[11px] text-faint sm:inline">
            approval queue
          </span>
        </div>
        <div className="flex items-center gap-4">
          <Link href="/" className="font-mono text-xs text-dim hover:text-fg">
            ← console
          </Link>
          <SystemStatus />
        </div>
      </header>

      {/* title */}
      <section className="pt-8">
        <h1 className="font-display text-3xl font-semibold tracking-tight text-fg sm:text-4xl">
          Human approval
        </h1>
        <p className="mt-3 max-w-xl text-[15px] leading-relaxed text-dim">
          High-risk actions stop here. Nothing has run yet — approving fires the tool,
          rejecting closes the item.
        </p>
      </section>

      {/* action feedback */}
      {notice && (
        <div
          className="mt-6 rounded-xl p-3.5 text-sm"
          style={{
            background: `color-mix(in oklab, ${noticeColor(notice.kind)} 8%, transparent)`,
            boxShadow: `inset 0 0 0 1px color-mix(in oklab, ${noticeColor(notice.kind)} 32%, transparent)`,
            color: "var(--color-fg)",
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
        </div>
      )}

      {/* queue */}
      <section className="mt-8 space-y-4">
        {!loading && !error && items.length === 0 ? (
          <div className="rounded-2xl bg-surface p-10 text-center" style={{ boxShadow: "inset 0 0 0 1px var(--color-edge)" }}>
            <p className="text-sm text-dim">The queue is clear.</p>
            <p className="mt-1 font-mono text-xs text-faint">
              High-risk actions from the console will appear here for approval.
            </p>
          </div>
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
        {loading && (
          <p className="text-center font-mono text-xs text-faint">Loading queue…</p>
        )}
      </section>
    </main>
  );
}

function noticeColor(kind: Notice["kind"]): string {
  return kind === "ok"
    ? "var(--color-answer)"
    : kind === "warn"
      ? "var(--color-action)"
      : "var(--color-escalate)";
}

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
  const c = RISK_COLOR[item.risk_level] ?? "var(--color-spam)";
  const working = busy !== undefined;

  return (
    <article
      className="animate-rise overflow-hidden rounded-2xl bg-surface"
      style={{
        boxShadow: `inset 0 0 0 1px var(--color-edge), 0 0 0 1px color-mix(in oklab, ${c} 22%, transparent), 0 24px 60px -30px color-mix(in oklab, ${c} 40%, transparent)`,
      }}
    >
      <div className="h-0.5 w-full" style={{ background: c }} />
      <div className="space-y-4 p-5 sm:p-6">
        {/* header row */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <RiskBadge level={item.risk_level} />
          <span className="font-mono text-sm text-fg">{item.tool}</span>
          <span className="font-mono text-xs text-faint">#{item.id}</span>
          <span className="ml-auto font-mono text-[11px] text-faint">{ago(item.created_at)}</span>
        </div>

        {/* originating request */}
        {item.request && (
          <p className="text-sm text-dim">
            <span className="font-mono text-faint">request&nbsp;›&nbsp;</span>
            {item.request}
          </p>
        )}

        {/* params the tool would run with */}
        <div
          className="rounded-xl p-4"
          style={{
            background: "color-mix(in oklab, var(--color-surface-2) 60%, transparent)",
            boxShadow: "inset 0 0 0 1px var(--color-edge)",
          }}
        >
          <p className="mb-2 font-mono text-[11px] uppercase tracking-[0.18em] text-faint">
            Tool parameters
          </p>
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 font-mono text-xs">
            {Object.entries(item.params).map(([k, v]) => (
              <div key={k} className="contents">
                <dt className="text-faint">{k}</dt>
                <dd className="break-words text-dim">{String(v)}</dd>
              </div>
            ))}
          </dl>
        </div>

        {/* decision */}
        <div className="flex items-center justify-end gap-2.5 pt-1">
          <Button
            variant="destructive"
            size="sm"
            disabled={working}
            onClick={onReject}
          >
            {busy === "reject" ? "Rejecting…" : "Reject"}
          </Button>
          <Button size="sm" disabled={working} onClick={onApprove}>
            {busy === "approve" ? "Approving…" : "Approve & run"}
          </Button>
        </div>
      </div>
    </article>
  );
}
