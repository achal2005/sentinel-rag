"use client";

import { useState } from "react";
import { triage } from "@/lib/api";
import type { RouteKey, TriageRecord } from "@/lib/types";
import { PipelineRail } from "@/components/console/pipeline-rail";
import { RequestConsole } from "@/components/console/request-console";
import { TriageRecordCard } from "@/components/console/triage-record";

export default function ConsolePage() {
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
    <div className="mx-auto w-full max-w-6xl px-5 py-10 sm:px-8 sm:py-12">
      <div className="max-w-4xl">
      {/* header */}
      <div>
        <p className="eyebrow text-brand">Live console</p>
        <h1 className="mt-1.5 font-display text-2xl font-semibold tracking-tight text-fg sm:text-[28px]">
          Observe one decision end to end
        </h1>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-dim">
          Submit a Meridian support request. The response below comes from the live
          graph, including its real route, evidence, latency, tokens and persisted run ID.
        </p>
      </div>

      {/* pipeline */}
      <div className="animate-fade mt-7">
        <PipelineRail active={pending ? null : lastRoute} processing={pending} />
      </div>

      {/* composer */}
      <div className="mt-7 flex justify-start">
        <RequestConsole onSubmit={handleSubmit} pending={pending} lastRoute={lastRoute} />
      </div>

      {/* error */}
      {error && (
        <div
          className="mt-7 rounded-xl p-4 text-sm text-fg"
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
      <section className="mt-10 space-y-4">
        {records.length === 0 && !error ? (
          <p className="text-center font-mono text-xs text-faint">
            Submit a request to see how Sentinel triages it.
          </p>
        ) : (
          <div className="flex items-center justify-between">
            <p className="eyebrow">Triage records</p>
            <span className="font-mono text-[11px] text-faint">{records.length} this session</span>
          </div>
        )}
        {records.map((r) => (
          <TriageRecordCard key={r.id} record={r} />
        ))}
      </section>
      </div>
    </div>
  );
}
