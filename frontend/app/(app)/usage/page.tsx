"use client";

import { useEffect, useState } from "react";
import { fetchStats, fetchEvals } from "@/lib/api";
import type { EvalSummary, UsageStat, UsageStats } from "@/lib/types";
import { StatCard } from "@/components/console/stat-card";

const TONE: Record<string, string> = {
  neutral: "var(--color-fg)",
  brand: "var(--color-brand)",
  answer: "var(--color-answer)",
  action: "var(--color-action)",
  escalate: "var(--color-escalate)",
  spam: "var(--color-spam)",
};
const CYCLE = ["brand", "action", "answer", "spam"] as const;

const dollars = (n: number) => `$${n.toFixed(n === 0 ? 2 : 4)}`;
const pct = (n: number) => `${Math.round(n * 100)}%`;

function channelLabel(raw: string): string {
  if (raw === "web_form") return "Web form";
  if (raw === "whatsapp") return "WhatsApp";
  if (raw === "email") return "Email";
  return raw.charAt(0).toUpperCase() + raw.slice(1);
}

export default function UsagePage() {
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [evals, setEvals] = useState<EvalSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      const [s, e] = await Promise.allSettled([fetchStats(), fetchEvals()]);
      if (!alive) return;
      if (s.status === "fulfilled") setStats(s.value);
      else setError(s.reason instanceof Error ? s.reason.message : "Failed to load stats.");
      if (e.status === "fulfilled") setEvals(e.value);
      setLoading(false);
    })();
    return () => {
      alive = false;
    };
  }, []);

  const statCards: UsageStat[] = stats
    ? [
        { label: "Requests today", value: stats.requests_today, hint: "triaged today", tone: "brand" },
        { label: "Pending approvals", value: stats.pending_approvals, hint: "awaiting sign-off", tone: "action" },
        { label: "Avg. latency", value: stats.avg_latency_ms / 1000, suffix: "s", decimals: 1, hint: "router → outcome", tone: "neutral" },
        { label: "Escalation rate", value: Math.round(stats.escalation_rate * 100), suffix: "%", hint: "handed to a human", tone: "escalate" },
      ]
    : [];

  return (
    <div className="mx-auto w-full max-w-6xl px-5 py-10 sm:px-8 sm:py-12">
      <div>
        <p className="eyebrow text-brand">Observability</p>
        <h1 className="mt-1.5 font-display text-2xl font-semibold tracking-tight text-fg sm:text-[28px]">
          Evidence from every run
        </h1>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-dim">
          Cost, latency, routing and evaluation data are read from persisted run records
          and the latest generated report—not hand-entered dashboard figures.
        </p>
      </div>

      {loading ? (
        <LoadingSkeleton />
      ) : (
        <>
          {/* cost */}
          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            <CostCard
              label="Cost today"
              value={stats ? dollars(stats.cost_today) : "—"}
              note={stats ? `${stats.requests_today} requests handled` : "Connect the API to read run records"}
              primary
            />
            <CostCard
              label="Month to date"
              value={stats ? dollars(stats.cost_mtd) : "—"}
              note={stats ? "recorded from persisted token usage" : "No value shown without persisted data"}
            />
          </div>

          {error && !stats ? (
            <div className="mt-4 rounded-2xl clay bg-surface p-5 text-sm">
              <p className="font-medium text-escalate">{error}</p>
              <p className="mt-1 font-mono text-xs text-dim">
                Start the API to see live usage: <span className="text-fg">uvicorn app.main:app --port 8000</span>
              </p>
            </div>
          ) : (
            <>
              {/* stat cards */}
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {statCards.map((s) => (
                  <StatCard key={s.label} stat={s} />
                ))}
              </div>

              {stats && stats.requests_today === 0 && (
                <p className="mt-3 text-xs leading-relaxed text-dim">
                  No requests handled yet today—these figures stay at zero until the first run,
                  then the console will populate them live.
                </p>
              )}

              {/* breakdowns */}
              <div className="mt-8 grid gap-4 lg:grid-cols-2">
                <BreakdownPanel
                  title="Model usage"
                  caption="calls today"
                  rows={(stats?.model_split ?? []).map((r, i) => ({
                    label: r.label,
                    count: r.count,
                    tone: CYCLE[i % CYCLE.length],
                  }))}
                />
                <BreakdownPanel
                  title="Requests by channel"
                  caption="requests today"
                  rows={(stats?.channel_split ?? []).map((r, i) => ({
                    label: channelLabel(r.label),
                    count: r.count,
                    tone: CYCLE[i % CYCLE.length],
                  }))}
                />
              </div>
            </>
          )}

          {/* reliability / evals — REAL numbers from evals/reports/latest.json */}
          <Reliability evals={evals} />
        </>
      )}
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div aria-hidden className="animate-none">
      {/* cost */}
      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        {[0, 1].map((i) => (
          <div key={i} className="rounded-2xl clay bg-surface p-5">
            <div className="skeleton h-3 w-24" />
            <div className="skeleton mt-2 h-10 w-32" />
            <div className="skeleton mt-2 h-3.5 w-40" />
          </div>
        ))}
      </div>

      {/* stat cards */}
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="rounded-2xl clay bg-surface p-5">
            <div className="skeleton h-3 w-20" />
            <div className="skeleton mt-2 h-8 w-16" />
            <div className="skeleton mt-2 h-3 w-24" />
          </div>
        ))}
      </div>

      {/* breakdowns */}
      <div className="mt-8 grid gap-4 lg:grid-cols-2">
        {[0, 1].map((i) => (
          <div key={i} className="rounded-2xl clay bg-surface p-5">
            <div className="flex items-baseline justify-between">
              <div className="skeleton h-3.5 w-28" />
              <div className="skeleton h-3 w-16" />
            </div>
            <div className="mt-4 space-y-3">
              {[0, 1, 2].map((j) => (
                <div key={j}>
                  <div className="mb-1.5 flex items-center justify-between gap-2">
                    <div className="skeleton h-3.5 w-24" />
                    <div className="skeleton h-3 w-6" />
                  </div>
                  <div className="skeleton h-2 w-full" />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function CostCard({ label, value, note, primary }: { label: string; value: string; note: string; primary?: boolean }) {
  return (
    <div
      className="rounded-2xl clay bg-surface p-5"
      style={primary ? { boxShadow: "var(--clay-shadow), 0 0 0 1px color-mix(in oklab, var(--color-brand) 22%, transparent)" } : undefined}
    >
      <p className="eyebrow">{label}</p>
      <p className="mt-2 font-display text-4xl font-semibold tracking-tight" style={{ color: primary ? "var(--color-brand)" : "var(--color-fg)" }}>
        {value}
      </p>
      <p className="mt-1.5 text-sm text-dim">{note}</p>
    </div>
  );
}

function BreakdownPanel({
  title,
  caption,
  rows,
}: {
  title: string;
  caption: string;
  rows: { label: string; count: number; tone: string }[];
}) {
  const max = Math.max(...rows.map((r) => r.count), 1);
  return (
    <div className="rounded-2xl clay bg-surface p-5">
      <div className="flex items-baseline justify-between">
        <h2 className="text-sm font-medium text-fg">{title}</h2>
        <span className="eyebrow">{caption}</span>
      </div>
      {rows.length === 0 ? (
        <div className="mt-4">
          <p className="font-mono text-xs text-faint">No data yet today.</p>
          <p className="mt-1 text-xs leading-relaxed text-dim">
            No requests handled yet today—this panel will populate as runs come in.
          </p>
        </div>
      ) : (
        <ul className="mt-4 space-y-3">
          {rows.map((r) => {
            const c = TONE[r.tone];
            return (
              <li key={r.label}>
                <div className="mb-1.5 flex items-center justify-between gap-2">
                  <span className="truncate text-sm text-dim">{r.label}</span>
                  <span className="font-mono text-xs text-faint">{r.count}</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full clay-inset bg-surface-2">
                  <div className="h-full rounded-full" style={{ width: `${(r.count / max) * 100}%`, background: `color-mix(in oklab, ${c} 80%, transparent)` }} />
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function Reliability({ evals }: { evals: EvalSummary | null }) {
  return (
    <section className="mt-10">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="eyebrow">Reliability · evals</p>
          <h2 className="mt-1.5 font-display text-lg font-semibold tracking-tight text-fg">
            Measured, not vibe-checked
          </h2>
        </div>
        {evals && (
          <div className="flex items-center gap-2 font-mono text-xs text-faint">
            <span className="size-1.5 rounded-full bg-answer" style={{ boxShadow: "0 0 7px var(--color-answer)" }} />
            {evals.passed}/{evals.total} passing · {pct(evals.passRate)}
          </div>
        )}
      </div>

      {!evals ? (
        <div className="mt-4 rounded-2xl clay bg-surface p-5 text-sm text-dim">
          No eval report found. Run the suite: <span className="font-mono text-fg">python -m evals.runners.run_golden</span>
        </div>
      ) : (
        <>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {evals.capabilities.slice(0, 6).map((cap, i) => (
              <ScoreCard key={cap.key} label={cap.label} rate={cap.rate} passed={cap.passed} denom={cap.denominator} tone={CYCLE[i % CYCLE.length]} />
            ))}
          </div>
          <p className="mt-4 font-mono text-[11px] leading-relaxed text-faint">
            {evals.dataset ?? "golden set"}
            {evals.version ? ` v${evals.version}` : ""} · {evals.total} executed / {evals.totalCases ?? evals.total} in dataset · tools:{" "}
            {evals.tools.join(", ") || "—"}
            {` · judge: ${evals.semanticJudge && evals.semanticJudge !== "none" ? evals.semanticJudge : "deterministic"}`}
            {evals.generatedAt ? ` · generated ${new Date(evals.generatedAt).toLocaleString()}` : ""}
          </p>
        </>
      )}
    </section>
  );
}

function ScoreCard({ label, rate, passed, denom, tone }: { label: string; rate: number; passed: number; denom: number; tone: string }) {
  const c = TONE[tone];
  return (
    <div className="rounded-2xl clay bg-surface p-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-dim">{label}</p>
        <span className="font-display text-lg font-semibold tabular-nums" style={{ color: c }}>
          {Math.round(rate * 100)}%
        </span>
      </div>
      <div className="mt-2.5 h-1.5 w-full overflow-hidden rounded-full clay-inset bg-surface-2">
        <div className="h-full rounded-full" style={{ width: `${rate * 100}%`, background: c }} />
      </div>
      <p className="mt-2 font-mono text-[11px] text-faint">{passed}/{denom} checks</p>
    </div>
  );
}
