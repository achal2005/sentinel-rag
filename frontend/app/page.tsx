"use client";

import Link from "next/link";
import {
  ArrowRight,
  Check,
  FileCheck2,
  Fingerprint,
  ShieldCheck,
  Workflow,
} from "lucide-react";
import { useEffect, useState } from "react";
import { HandwritingSvg } from "@/components/ui/handwriting-svg";
import { fetchEvals, fetchStats, fetchSystem } from "@/lib/api";
import type { EvalSummary, SystemInfo, UsageStats } from "@/lib/types";

const OUTCOMES = [
  { key: "answer", label: "Answer", line: "Cite the exact passage and answer from evidence.", color: "var(--color-answer)" },
  { key: "action", label: "Act", line: "Validate parameters, then call an allow-listed workflow.", color: "var(--color-action)" },
  { key: "escalate", label: "Escalate", line: "Hand uncertainty or risk to a human with context intact.", color: "var(--color-escalate)" },
  { key: "reject", label: "Reject", line: "Stop prompt injection, spam, and requests outside policy.", color: "var(--color-spam)" },
] as const;

export default function Landing() {
  const [evals, setEvals] = useState<EvalSummary | null>(null);
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [system, setSystem] = useState<SystemInfo | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.allSettled([fetchEvals(), fetchStats(), fetchSystem()]).then(([evaluation, usage, runtime]) => {
      if (!active) return;
      if (evaluation.status === "fulfilled") setEvals(evaluation.value);
      if (usage.status === "fulfilled") setStats(usage.value);
      if (runtime.status === "fulfilled") setSystem(runtime.value);
      setChecked(true);
    });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="landing-shell min-h-full overflow-hidden">
      <header className="landing-nav mx-auto flex w-full max-w-[1240px] items-center justify-between px-5 py-5 sm:px-8">
        <Brand href="/" />
        <nav className="flex items-center gap-1 sm:gap-6" aria-label="Primary navigation">
          <a href="#how-it-works" className="nav-text hidden sm:inline-flex">How it works</a>
          <a href="#proof" className="nav-text hidden sm:inline-flex">Proof</a>
          <Link href="/inbox" className="nav-text hidden md:inline-flex">Run log</Link>
          <Link href="/console" className="button-primary group">
            Open console
            <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
          </Link>
        </nav>
      </header>

      <main>
        <section className="hero-grid mx-auto grid w-full max-w-[1240px] gap-12 px-5 pb-24 pt-16 sm:px-8 sm:pt-24 lg:grid-cols-[1.03fr_.97fr] lg:items-center lg:gap-20 lg:pb-32 lg:pt-28">
          <div className="relative z-10">
            <p className="reveal-up eyebrow flex items-center gap-2 text-brand">
              <span className="size-1.5 rounded-full bg-brand" />
              Evidence-first support operations
            </p>
            <h1 className="reveal-up mt-6 max-w-[760px] font-display text-[50px] font-medium leading-[0.96] tracking-[-0.055em] text-fg sm:text-[72px] lg:text-[82px]">
              Support that can
              <span className="block text-dim">show its work.</span>
            </h1>

            <div className="reveal-up handwriting-lockup -ml-1 mt-2 h-[82px] text-brand sm:h-[96px]" style={{ animationDelay: "120ms" }}>
              <HandwritingSvg
                text="proof, attached."
                width={430}
                height={96}
                fontSize={66}
                duration={2.4}
                delay={0.7}
                strokeWidth={1.15}
                className="h-full w-full max-w-[430px]"
              />
            </div>

            <p className="reveal-up mt-4 max-w-xl text-[16px] leading-7 text-dim sm:text-[17px]" style={{ animationDelay: "160ms" }}>
              Sentinel reads the request, retrieves the evidence, and chooses one safe outcome: answer, act, escalate, or reject. Every decision keeps its sources and audit trail.
            </p>

            <div className="reveal-up mt-8 flex flex-wrap items-center gap-3" style={{ animationDelay: "220ms" }}>
              <Link href="/console" className="button-primary group px-5 py-3">
                Run a real request
                <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
              </Link>
              <Link href="/usage" className="button-secondary px-5 py-3">Read the evidence report</Link>
            </div>

            <dl className="reveal-fade mt-10 grid max-w-2xl grid-cols-3 border-y border-edge/80" style={{ animationDelay: "320ms" }}>
              <Proof value={evals ? `${evals.passed}/${evals.total}` : "—"} label="checks passing" />
              <Proof value={evals?.criticalPassed ? "PASS" : evals ? "REVIEW" : "—"} label="policy gate" />
              <Proof value={system?.tools.length ? String(system.tools.length) : evals?.tools.length ? String(evals.tools.length) : "—"} label="safe tools" last />
            </dl>
          </div>

          <DecisionReceipt system={system} checked={checked} />
        </section>

        <section id="how-it-works" className="scroll-mt-20 border-y border-edge bg-surface/35">
          <div className="mx-auto grid w-full max-w-[1240px] gap-12 px-5 py-20 sm:px-8 sm:py-28 lg:grid-cols-[.75fr_1.25fr] lg:gap-24">
            <div className="lg:sticky lg:top-24 lg:self-start">
              <p className="eyebrow text-brand">One request. A visible decision.</p>
              <h2 className="mt-5 max-w-md font-display text-4xl font-medium leading-[1.02] tracking-[-0.04em] text-fg sm:text-5xl">The route is part of the answer.</h2>
              <p className="mt-5 max-w-md text-[15px] leading-7 text-dim">The system does not pretend every message is a question. It separates knowledge work from side effects and keeps uncertainty visible.</p>
            </div>

            <div className="outcome-ledger border-t border-edge">
              {OUTCOMES.map((outcome, index) => (
                <article key={outcome.key} className="outcome-row group grid gap-4 border-b border-edge py-6 sm:grid-cols-[80px_150px_1fr] sm:items-center">
                  <span className="font-mono text-[11px] text-faint">0{index + 1}</span>
                  <h3 className="font-display text-2xl font-medium tracking-[-0.025em]" style={{ color: outcome.color }}>{outcome.label}</h3>
                  <p className="max-w-md text-sm leading-6 text-dim">{outcome.line}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto w-full max-w-[1240px] px-5 py-20 sm:px-8 sm:py-28">
          <div className="grid gap-12 lg:grid-cols-[1.05fr_.95fr] lg:items-center lg:gap-20">
            <ApprovalStory />
            <div>
              <p className="eyebrow text-action">Human control, where it matters</p>
              <h2 className="mt-5 max-w-lg font-display text-4xl font-medium leading-[1.03] tracking-[-0.04em] text-fg sm:text-5xl">Automation earns permission one action at a time.</h2>
              <p className="mt-5 max-w-lg text-[15px] leading-7 text-dim">Low-risk, allow-listed work can move. Refunds, cancellations, and other high-risk changes stop in an approval queue with the exact parameters exposed before execution.</p>
              <ul className="mt-8 space-y-4">
                <Feature icon={Workflow} title="Allow-listed workflows" body="The model can select registered tools; it cannot invent a new side effect." />
                <Feature icon={ShieldCheck} title="Risk-aware approvals" body="Policy decides what runs automatically and what waits for a person." />
                <Feature icon={Fingerprint} title="Persisted audit trail" body="Route, evidence, tokens, latency, tool inputs, and decisions stay inspectable." />
              </ul>
            </div>
          </div>
        </section>

        <section id="proof" className="proof-field scroll-mt-20 border-y border-edge">
          <div className="mx-auto w-full max-w-[1240px] px-5 py-20 sm:px-8 sm:py-28">
            <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="eyebrow text-answer">Measured reliability</p>
                <h2 className="mt-5 max-w-2xl font-display text-4xl font-medium leading-[1.03] tracking-[-0.04em] text-fg sm:text-5xl">The report is allowed to disagree with the pitch.</h2>
              </div>
              <Link href="/usage" className="button-secondary self-start sm:self-auto">Open observability <ArrowRight className="size-3.5" /></Link>
            </div>

            {evals ? (
              <div className="mt-12 border-t border-edge">
                {evals.capabilities.slice(0, 6).map((capability) => (
                  <div key={capability.key} className="score-row grid gap-3 border-b border-edge py-5 sm:grid-cols-[1fr_2fr_auto] sm:items-center">
                    <p className="text-sm font-medium text-fg">{capability.label}</p>
                    <div className="h-1 overflow-hidden bg-surface-2"><div className="h-full bg-answer" style={{ width: `${Math.min(100, capability.rate * 100)}%` }} /></div>
                    <p className="font-mono text-xs text-faint"><span className="text-answer">{Math.round(capability.rate * 100)}%</span> · {capability.passed}/{capability.denominator}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-12 border-y border-edge py-8 text-sm text-dim">The evaluation report appears here when the local API is connected.</div>
            )}

            <div className="mt-8 flex flex-wrap gap-x-8 gap-y-3 font-mono text-[11px] text-faint">
              <span>{evals?.dataset ?? "Golden evaluation set"}</span>
              <span>{formatRunDate(evals?.generatedAt)}</span>
              <span>{evals?.semanticJudge && evals.semanticJudge !== "none" ? evals.semanticJudge : "Deterministic PR gate"}</span>
              <span>{stats ? `${money(stats.cost_today)} recorded today` : "No invented live metrics"}</span>
            </div>
          </div>
        </section>

        <section className="mx-auto grid w-full max-w-[1240px] gap-12 px-5 py-20 sm:px-8 sm:py-28 lg:grid-cols-[.8fr_1.2fr] lg:gap-24">
          <div>
            <p className="eyebrow">Built for inspection</p>
            <h2 className="mt-5 font-display text-4xl font-medium leading-[1.03] tracking-[-0.04em] text-fg sm:text-5xl">Nothing important is hidden behind “AI.”</h2>
          </div>
          <div className="divide-y divide-edge border-y border-edge">
            <InfoRow question="Where did the answer come from?" answer="The request trace shows retrieved passages, confidence, and the citation IDs used in the response." />
            <InfoRow question="What happens when evidence is weak?" answer="The confidence gate stops the answer path and sends the request to a human instead." />
            <InfoRow question="Can the agent make risky changes alone?" answer="No. High-risk tool calls wait with their validated parameters in the approval queue." />
            <InfoRow question="Are the dashboard numbers real?" answer="The interface reads persisted runs and generated evaluation reports. Offline values stay unknown." />
          </div>
        </section>

        <section className="mx-5 mb-5 overflow-hidden border border-edge bg-surface sm:mx-8 sm:mb-8">
          <div className="mx-auto flex max-w-[1180px] flex-col gap-8 px-6 py-12 sm:px-10 sm:py-16 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="eyebrow text-brand">See the whole decision</p>
              <h2 className="mt-3 font-display text-3xl font-medium tracking-[-0.035em] text-fg sm:text-4xl">Give Sentinel a request. Inspect what it does next.</h2>
            </div>
            <Link href="/console" className="button-primary group self-start px-5 py-3 lg:self-auto">Open live console <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" /></Link>
          </div>
        </section>
      </main>

      <footer className="mx-auto flex w-full max-w-[1240px] flex-col gap-3 px-5 py-8 font-mono text-[10px] uppercase tracking-[0.12em] text-faint sm:flex-row sm:items-center sm:justify-between sm:px-8">
        <span>Sentinel · evidence-first support operations</span>
        <span>{system ? `${providerName(system.provider)} · ${providerName(system.embed_provider)} embeddings` : "model provider · embeddings"} · pgvector · LangGraph · n8n</span>
      </footer>
    </div>
  );
}

function DecisionReceipt({ system, checked }: { system: SystemInfo | null; checked: boolean }) {
  const online = Boolean(system);
  return (
    <aside className="receipt-wrap reveal-up relative lg:ml-auto" style={{ animationDelay: "130ms" }} aria-label="Example Sentinel decision receipt">
      <div className="receipt-tab" aria-hidden>decision / 2048</div>
      <div className="receipt-card">
        <div className="flex items-center justify-between gap-4 border-b border-edge px-5 py-4 sm:px-6">
          <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.15em] text-faint">
            <span className={`size-1.5 rounded-full ${online ? "bg-answer" : "bg-faint"}`} />
            {online ? "live runtime" : checked ? "preview · API offline" : "checking runtime"}
          </div>
          <span className="font-mono text-[10px] text-faint">web · just now</span>
        </div>

        <div className="space-y-6 px-5 py-6 sm:px-6 sm:py-7">
          <div>
            <p className="eyebrow">Incoming request</p>
            <p className="mt-3 text-[15px] leading-6 text-fg">How do I rotate a Meridian secret API key without downtime?</p>
          </div>
          <div className="route-strip grid grid-cols-[auto_1fr_auto_1fr_auto] items-center gap-2 font-mono text-[9px] uppercase tracking-[0.13em] text-faint">
            <span>ingest</span><i /><span className="text-brand">route</span><i /><span className="text-answer">answer</span>
          </div>
          <div className="border-l-2 border-answer pl-4">
            <div className="mb-2 flex items-center gap-2"><span className="status-stamp text-answer">grounded answer</span><span className="font-mono text-[10px] text-faint">0.91 confidence</span></div>
            <p className="text-[15px] leading-7 text-fg">Rotate it under <strong className="font-medium text-white">Settings → API Keys</strong>. Meridian issues a new secret and keeps the old one valid for a grace window you choose (up to 7 days), so there is no downtime <Citation id="key-06" /></p>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            <ReceiptFact label="source" value="api-keys.md" />
            <ReceiptFact label="runtime" value={system?.chat_model ?? "local answer model"} />
          </div>
          <div className="flex items-center justify-between border-t border-dashed border-edge pt-4">
            <div className="flex items-center gap-2 text-xs text-dim"><FileCheck2 className="size-4 text-answer" />Evidence attached</div>
            <span className="font-mono text-[10px] text-faint">audit saved</span>
          </div>
        </div>
      </div>
      <div className="receipt-note"><Check className="size-3" /> no guesswork</div>
    </aside>
  );
}

function ApprovalStory() {
  return (
    <div className="approval-sheet relative" aria-label="Example approval decision">
      <div className="flex items-start justify-between gap-4 border-b border-edge px-5 py-5 sm:px-7">
        <div><p className="eyebrow text-action">Approval required</p><p className="mt-2 text-lg font-medium text-fg">Cancel invoice INV-2231</p></div>
        <span className="status-stamp text-escalate">high risk</span>
      </div>
      <dl className="grid grid-cols-[100px_1fr] gap-y-3 px-5 py-6 font-mono text-xs sm:px-7">
        <dt className="text-faint">customer</dt><dd className="text-dim">alex@example.com</dd>
        <dt className="text-faint">amount</dt><dd className="text-fg">$129.00</dd>
        <dt className="text-faint">reason</dt><dd className="text-dim">duplicate charge reported</dd>
        <dt className="text-faint">workflow</dt><dd className="text-dim">cancel_invoice</dd>
      </dl>
      <div className="flex items-center justify-between gap-4 border-t border-edge bg-ink/35 px-5 py-4 sm:px-7">
        <span className="font-mono text-[10px] text-faint">Held · not executed</span>
        <div className="flex gap-2"><span className="button-quiet">Reject</span><span className="button-primary">Approve & run</span></div>
      </div>
    </div>
  );
}

function Feature({ icon: Icon, title, body }: { icon: typeof Workflow; title: string; body: string }) {
  return <li className="grid grid-cols-[auto_1fr] gap-4"><span className="mt-0.5 grid size-8 place-items-center border border-edge bg-surface text-brand"><Icon className="size-4" /></span><div><p className="text-sm font-medium text-fg">{title}</p><p className="mt-1 text-sm leading-6 text-dim">{body}</p></div></li>;
}

function InfoRow({ question, answer }: { question: string; answer: string }) {
  return <div className="grid gap-2 py-6 sm:grid-cols-[.85fr_1.15fr] sm:gap-8"><h3 className="text-sm font-medium text-fg">{question}</h3><p className="text-sm leading-6 text-dim">{answer}</p></div>;
}

function ReceiptFact({ label, value }: { label: string; value: string }) {
  return <div className="border border-edge bg-ink/35 px-3 py-3"><p className="font-mono text-[9px] uppercase tracking-[0.13em] text-faint">{label}</p><p className="mt-1 truncate font-mono text-[11px] text-dim">{value}</p></div>;
}

function Citation({ id }: { id: string }) {
  return <code className="citation-token">{id}</code>;
}

function Proof({ value, label, last }: { value: string; label: string; last?: boolean }) {
  return <div className={`py-4 pr-4 sm:pr-6 ${last ? "pl-4 sm:pl-6" : "border-r border-edge px-4 first:pl-0 sm:px-6"}`}><dt className="font-display text-2xl font-medium tabular-nums tracking-[-0.03em] text-fg">{value}</dt><dd className="mt-1 font-mono text-[9px] uppercase tracking-[0.1em] text-faint">{label}</dd></div>;
}

function Brand({ href }: { href: string }) {
  return <Link href={href} className="group inline-flex items-center gap-3" aria-label="Sentinel home"><span className="sentinel-mark" aria-hidden><span /></span><span><span className="block font-display text-[16px] font-semibold leading-none tracking-[-0.02em] text-fg">Sentinel</span><span className="mt-1 block font-mono text-[8px] uppercase tracking-[0.18em] text-faint">evidence desk</span></span></Link>;
}

function money(value: number): string {
  return `$${value.toFixed(value === 0 ? 2 : 4)}`;
}

function formatRunDate(value: string | null | undefined): string {
  if (!value) return "Latest checked-in report";
  return new Intl.DateTimeFormat("en", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(value));
}

function providerName(value: string): string {
  if (value.toLowerCase() === "gemini") return "Gemini";
  if (value.toLowerCase() === "ollama") return "Ollama";
  return value;
}
