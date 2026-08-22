"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Activity,
  ArrowRight,
  Boxes,
  Cpu,
  Database,
  FlaskConical,
  ShieldCheck,
  Workflow,
} from "lucide-react";
import { InteractiveStarfieldHero } from "@/components/starfield-hero";
import { SentinelLogo } from "@/components/brand/sentinel-logo";
import { fetchEvals, fetchSystem } from "@/lib/api";
import type { EvalSummary, SystemInfo } from "@/lib/types";

const EASE = [0.22, 1, 0.36, 1] as const;

/* pipeline stages (the spine of the system) */
const OUTCOMES = [
  { label: "Answer", color: "var(--color-answer)", note: "cited from docs" },
  { label: "Act", color: "var(--color-action)", note: "allow-listed tool" },
  { label: "Escalate", color: "var(--color-escalate)", note: "hand to a human" },
  { label: "Reject", color: "var(--color-spam)", note: "spam / injection" },
] as const;

const STACK = [
  "FastAPI",
  "LangGraph",
  "Python 3.12",
  "Postgres + pgvector",
  "Ollama",
  "Gemini",
  "n8n",
  "Langfuse",
  "Next.js 16",
  "Docker",
];

export default function ArchitecturePage() {
  const [system, setSystem] = useState<SystemInfo | null>(null);
  const [evals, setEvals] = useState<EvalSummary | null>(null);

  useEffect(() => {
    let alive = true;
    Promise.allSettled([fetchSystem(), fetchEvals()]).then(([s, e]) => {
      if (!alive) return;
      if (s.status === "fulfilled") setSystem(s.value);
      if (e.status === "fulfilled") setEvals(e.value);
    });
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="relative min-h-full overflow-x-hidden">
      {/* nav */}
      <header className="fixed inset-x-0 top-0 z-50">
        <div className="mx-auto flex w-full max-w-[1220px] items-center justify-between px-5 py-4 sm:px-8">
          <Link href="/" aria-label="Sentinel home">
            <SentinelLogo />
          </Link>
          <nav className="flex items-center gap-1 sm:gap-5" aria-label="Primary">
            <Link href="/inbox" className="nav-link hidden sm:inline">Run log</Link>
            <Link href="/usage" className="nav-link hidden sm:inline">Observability</Link>
            <Link href="/console" className="beacon-btn group">
              Open console
              <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
            </Link>
          </nav>
        </div>
      </header>

      {/* header band over the particle field */}
      <InteractiveStarfieldHero
        className="min-h-[62vh] rounded-none bg-ink"
        particleColor="#8fe0cb"
        activeColor="#eafff7"
        particleCount={300}
        interactionRadius={160}
        speed={0.4}
      >
        <div className="mx-auto w-full max-w-[1220px]">
          <span className="chip">
            <span className="size-1.5 animate-pulse rounded-full bg-brand" />
            System architecture
          </span>
          <h1 className="mt-7 max-w-3xl font-display text-[46px] font-normal leading-[0.98] tracking-[-0.02em] text-fg sm:text-[76px]">
            One request,
            <br />
            <span className="italic text-brand">six layers of accountability.</span>
          </h1>
          <p className="mt-6 max-w-xl text-[16px] leading-7 text-dim sm:text-[17px]">
            Sentinel is an evidence-first support operator. Every request flows
            through the same spine — retrieve, decide, gate, act, and record —
            with a human in the loop wherever a decision carries real risk.
          </p>
        </div>
      </InteractiveStarfieldHero>

      {/* pipeline spine */}
      <section className="relative border-t border-edge bg-surface/30">
        <div className="mx-auto w-full max-w-[1220px] px-5 py-20 sm:px-8">
          <Reveal>
            <p className="eyebrow text-brand">The spine</p>
            <h2 className="mt-4 font-display text-3xl leading-tight text-fg sm:text-5xl">
              Request in. Accountable decision out.
            </h2>
          </Reveal>
          <Reveal delay={0.08}>
            <Pipeline />
          </Reveal>
        </div>
      </section>

      {/* bento layers */}
      <section className="relative border-t border-edge">
        <div className="mx-auto w-full max-w-[1220px] px-5 py-20 sm:px-8">
          <Reveal>
            <p className="eyebrow text-answer">The layers</p>
            <h2 className="mt-4 font-display text-3xl leading-tight text-fg sm:text-5xl">
              Six responsibilities, cleanly separated.
            </h2>
          </Reveal>

          <div className="mt-12 grid auto-rows-[1fr] gap-4 md:grid-cols-3">
            {/* wide feature cell */}
            <BentoCard
              className="md:col-span-2"
              icon={Database}
              color="var(--color-answer)"
              kicker="Brain · retrieval"
              title="Grounded answers, or nothing"
              body="Hybrid vector + full-text retrieval over pgvector, fused with Reciprocal Rank Fusion and gated on cosine confidence. If the top passage isn't strong enough, Sentinel escalates instead of guessing — citations, or a human."
              chips={["pgvector", "hybrid + RRF", "citations-or-escalate"]}
            />
            <BentoCard
              icon={Workflow}
              color="var(--color-action)"
              kicker="Hands · tools"
              title="Controlled side effects"
              body="An allow-listed registry with Pydantic-validated parameters. Tools run as n8n webhooks; repeats are idempotent."
              chips={["n8n", "Pydantic", "risk tiers"]}
            />
            <BentoCard
              icon={ShieldCheck}
              color="var(--color-escalate)"
              kicker="Safety · gate"
              title="Human approval + critic"
              body="A deterministic critic screens every proposed action (block / revise / allow). High-risk actions wait in an approval queue before anything fires."
              chips={["deterministic critic", "approval_queue", "Basic auth"]}
            />
            <BentoCard
              icon={Activity}
              color="var(--color-brand)"
              kicker="Glass · observability"
              title="A complete audit trail"
              body="Every run logs its route, chunks, tool, tokens, cost and latency to Postgres, with a per-step audit log and optional Langfuse traces."
              chips={["runs", "audit_log", "Langfuse"]}
            />
            <BentoCard
              icon={FlaskConical}
              color="var(--color-answer)"
              kicker="Rigor · evals"
              title="Measured, then gated"
              body={
                evals
                  ? `A ${evals.totalCases ?? 300}-case suite with a deterministic PR gate (${evals.passed}/${evals.total}) plus a calibrated LLM judge.`
                  : "A 300-case suite with a deterministic PR gate plus a calibrated LLM judge, run in CI."
              }
              chips={["pytest", "GitHub Actions", "LLM judge"]}
            />
            <RuntimeCard system={system} />
          </div>
        </div>
      </section>

      {/* stack strip */}
      <section className="relative border-t border-edge bg-surface/30">
        <div className="mx-auto w-full max-w-[1220px] px-5 py-16 sm:px-8">
          <Reveal className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="eyebrow">Built with</p>
              <h2 className="mt-3 font-display text-2xl text-fg sm:text-3xl">
                Self-hosted, free, and reproducible.
              </h2>
            </div>
            <Link href="/console" className="beacon-btn group self-start px-5 py-3 text-[15px] sm:self-auto">
              See it run <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
          </Reveal>
          <Reveal delay={0.06} className="mt-8 flex flex-wrap gap-2.5">
            {STACK.map((s) => (
              <span
                key={s}
                className="rounded-lg border border-edge bg-ink px-3 py-1.5 font-mono text-xs text-dim"
              >
                {s}
              </span>
            ))}
          </Reveal>
        </div>
      </section>

      <footer className="border-t border-edge">
        <div className="mx-auto flex w-full max-w-[1220px] flex-col gap-3 px-5 py-8 font-mono text-[10px] uppercase tracking-[0.14em] text-faint sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <span>Sentinel · evidence-first support operations</span>
          <span className="flex items-center gap-2">
            <span className={`size-1.5 rounded-full ${system ? "bg-answer" : "bg-faint"}`} />
            {system ? "runtime online" : "runtime offline"} · FastAPI · LangGraph · Next.js
          </span>
        </div>
      </footer>
    </div>
  );
}

/* ── pipeline diagram ───────────────────────────────────────────── */

function Pipeline() {
  return (
    <div className="mt-12 rounded-2xl border border-edge bg-ink p-6 sm:p-9">
      {/* spine: request → api → router */}
      <div className="flex flex-col items-stretch gap-3 lg:flex-row lg:items-center">
        <Node label="Request" sub="web · email · chat" />
        <Connector />
        <Node label="FastAPI" sub="/triage" mono />
        <Connector />
        <Node label="LangGraph router" sub="triage decision" accent />
      </div>

      {/* fan-out to the four outcomes */}
      <div className="relative mt-3 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <span className="pointer-events-none absolute -top-3 left-1/2 hidden h-3 w-px -translate-x-1/2 bg-edge lg:block" />
        {OUTCOMES.map((o, i) => (
          <motion.div
            key={o.label}
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, ease: EASE, delay: i * 0.08 }}
            className="rounded-xl border border-edge bg-surface/50 px-4 py-3"
            style={{ boxShadow: `inset 0 0 0 1px color-mix(in oklab, ${o.color} 16%, transparent)` }}
          >
            <span className="flex items-center gap-2">
              <span
                className="size-2 rounded-full"
                style={{ background: o.color, boxShadow: `0 0 10px -1px ${o.color}` }}
              />
              <span className="font-display text-lg" style={{ color: o.color }}>
                {o.label}
              </span>
            </span>
            <span className="mt-1 block font-mono text-[11px] text-faint">{o.note}</span>
          </motion.div>
        ))}
      </div>

      {/* converge to the record */}
      <div className="mt-3 flex items-center gap-3">
        <span className="h-px flex-1 bg-edge" />
        <span className="rounded-full border border-edge bg-surface/60 px-4 py-1.5 font-mono text-[11px] text-dim">
          critic gate · approval queue · audit log · cost + Langfuse trace
        </span>
        <span className="h-px flex-1 bg-edge" />
      </div>
    </div>
  );
}

function Node({ label, sub, accent, mono }: { label: string; sub: string; accent?: boolean; mono?: boolean }) {
  return (
    <div
      className="flex-1 rounded-xl border bg-surface/50 px-4 py-3"
      style={{ borderColor: accent ? "color-mix(in oklab, var(--color-brand) 45%, var(--color-edge))" : "var(--color-edge)" }}
    >
      <p className={`text-sm font-semibold ${accent ? "text-brand" : "text-fg"}`}>{label}</p>
      <p className={`mt-0.5 text-[11px] text-faint ${mono ? "font-mono" : ""}`}>{sub}</p>
    </div>
  );
}

function Connector() {
  return (
    <span className="relative mx-auto hidden h-px w-8 shrink-0 bg-edge lg:block">
      <motion.span
        className="absolute top-1/2 size-1.5 -translate-y-1/2 rounded-full bg-brand"
        style={{ boxShadow: "0 0 8px 1px var(--color-brand)" }}
        initial={{ left: "-10%", opacity: 0 }}
        animate={{ left: ["-10%", "110%"], opacity: [0, 1, 0] }}
        transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut", repeatDelay: 0.6 }}
      />
    </span>
  );
}

/* ── bento cards ────────────────────────────────────────────────── */

function BentoCard({
  icon: Icon,
  color,
  kicker,
  title,
  body,
  chips,
  className,
}: {
  icon: typeof Database;
  color: string;
  kicker: string;
  title: string;
  body: string;
  chips: string[];
  className?: string;
}) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 22 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-10% 0px" }}
      transition={{ duration: 0.55, ease: EASE }}
      className={`group relative flex flex-col overflow-hidden rounded-2xl border border-edge bg-surface/40 p-6 transition-colors hover:border-edge-strong ${className ?? ""}`}
    >
      <span
        className="grid size-10 place-items-center rounded-xl border border-edge"
        style={{ background: `color-mix(in oklab, ${color} 12%, transparent)`, color }}
      >
        <Icon className="size-5" />
      </span>
      <p className="mt-5 font-mono text-[10px] uppercase tracking-[0.16em] text-faint">{kicker}</p>
      <h3 className="mt-2 font-display text-2xl leading-tight text-fg">{title}</h3>
      <p className="mt-2.5 flex-1 text-sm leading-6 text-dim">{body}</p>
      <div className="mt-5 flex flex-wrap gap-2">
        {chips.map((c) => (
          <span
            key={c}
            className="rounded-md border border-edge bg-ink px-2 py-1 font-mono text-[10px] text-dim"
          >
            {c}
          </span>
        ))}
      </div>
    </motion.article>
  );
}

function RuntimeCard({ system }: { system: SystemInfo | null }) {
  const rows: { k: string; v: string }[] = system
    ? [
        { k: "provider", v: system.provider },
        { k: "chat model", v: system.chat_model },
        { k: "embeddings", v: `${system.embed_provider} · ${system.embed_model ?? "—"}` },
        { k: "tools", v: system.tools.join(", ") || "—" },
      ]
    : [];
  return (
    <motion.article
      initial={{ opacity: 0, y: 22 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-10% 0px" }}
      transition={{ duration: 0.55, ease: EASE }}
      className="relative flex flex-col overflow-hidden rounded-2xl border border-edge bg-surface/40 p-6"
    >
      <span className="grid size-10 place-items-center rounded-xl border border-edge bg-brand/12 text-brand">
        <Cpu className="size-5" />
      </span>
      <p className="mt-5 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.16em] text-faint">
        <span className={`size-1.5 rounded-full ${system ? "bg-answer" : "bg-faint"}`} />
        {system ? "live runtime" : "runtime · offline"}
      </p>
      <h3 className="mt-2 font-display text-2xl leading-tight text-fg">Configured right now</h3>
      {system ? (
        <dl className="mt-4 flex-1 space-y-2.5 font-mono text-xs">
          {rows.map((r) => (
            <div key={r.k} className="flex items-start justify-between gap-3 border-b border-edge/50 pb-2.5">
              <dt className="text-faint">{r.k}</dt>
              <dd className="max-w-[62%] truncate text-right text-dim">{r.v}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className="mt-4 flex-1 text-sm leading-6 text-dim">
          Start the API to read the live model, retrieval, and tool configuration.
        </p>
      )}
      <div className="mt-5 flex flex-wrap gap-2">
        {["Docker", "docker compose"].map((c) => (
          <span key={c} className="rounded-md border border-edge bg-ink px-2 py-1 font-mono text-[10px] text-dim">
            <Boxes className="mr-1 inline size-3 align-[-2px]" />
            {c}
          </span>
        ))}
      </div>
    </motion.article>
  );
}

/* ── scroll reveal ──────────────────────────────────────────────── */

function Reveal({
  children,
  delay = 0,
  className,
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-12% 0px" }}
      transition={{ duration: 0.6, ease: EASE, delay }}
    >
      {children}
    </motion.div>
  );
}
