"use client";

import { useState } from "react";
import { triage } from "@/lib/api";
import type { RouteKey, TriageRecord } from "@/lib/types";
import { SystemStatus } from "@/components/console/system-status";
import { PipelineRail } from "@/components/console/pipeline-rail";
import { RequestConsole } from "@/components/console/request-console";
import { TriageRecordCard } from "@/components/console/triage-record";

export default function Home() {
  const [records, setRecords] = useState<TriageRecord[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const lastRoute: RouteKey | null = records[0]?.route ?? null;

  async function handleSubmit(query: string) {
    setPending(true);
    setError(null);
    try {
      const result = await triage(query);
      setRecords((prev) => [
        { ...result, id: crypto.randomUUID(), at: Date.now() },
        ...prev,
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-5 pb-24">
      {/* top bar */}
      <header className="flex items-center justify-between py-6">
        <div className="flex items-center gap-2.5">
          <SentinelMark />
          <span className="font-display text-lg font-semibold tracking-tight text-fg">
            Sentinel
          </span>
          <span className="hidden font-mono text-[11px] text-faint sm:inline">
            LLM brain · n8n hands
          </span>
        </div>
        <SystemStatus />
      </header>

      {/* hero — lead with the interaction, not a big number */}
      <section className="flex flex-col items-center pt-10 text-center sm:pt-16">
        <h1 className="animate-rise font-display text-4xl font-semibold leading-[1.05] tracking-tight text-fg sm:text-5xl">
          Triage that shows
          <br />
          its work.
        </h1>
        <p
          className="animate-rise mt-4 max-w-xl text-balance text-[15px] leading-relaxed text-dim"
          style={{ animationDelay: "60ms" }}
        >
          Sentinel routes every support request, answers only with citations it can
          prove, and escalates the rest to a human.
        </p>

        <div className="animate-fade mt-8 w-full" style={{ animationDelay: "160ms" }}>
          <PipelineRail active={pending ? null : lastRoute} processing={pending} />
        </div>

        <div className="animate-rise mt-8 flex w-full justify-center" style={{ animationDelay: "220ms" }}>
          <RequestConsole onSubmit={handleSubmit} pending={pending} lastRoute={lastRoute} />
        </div>
      </section>

      {/* error state — direction, not mood */}
      {error && (
        <div
          className="mt-8 rounded-xl p-4 text-sm text-fg"
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

      {/* transcript */}
      <section className="mt-12 space-y-4">
        {records.length === 0 && !error ? (
          <p className="text-center font-mono text-xs text-faint">
            Submit a request to see how Sentinel triages it.
          </p>
        ) : (
          <div className="flex items-center justify-between">
            <h2 className="font-mono text-[11px] uppercase tracking-[0.18em] text-faint">
              Triage records
            </h2>
            <span className="font-mono text-[11px] text-faint">{records.length} this session</span>
          </div>
        )}
        {records.map((r) => (
          <TriageRecordCard key={r.id} record={r} />
        ))}
      </section>
    </main>
  );
}

function SentinelMark() {
  // A stylized sentry "eye / signal" glyph — the watchtower motif.
  return (
    <span
      className="grid size-7 place-items-center rounded-lg"
      style={{ boxShadow: "inset 0 0 0 1px var(--color-edge)", background: "var(--color-surface)" }}
    >
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
        <circle cx="8" cy="8" r="2.2" fill="var(--color-brand)" />
        <circle
          cx="8"
          cy="8"
          r="5.4"
          stroke="var(--color-answer)"
          strokeWidth="1.3"
          strokeDasharray="2 2.4"
        />
      </svg>
    </span>
  );
}
