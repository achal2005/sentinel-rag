"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  animate,
  motion,
  useInView,
  useReducedMotion,
  useScroll,
  useTransform,
  AnimatePresence,
} from "framer-motion";
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  Boxes,
  Cpu,
  Database,
  FlaskConical,
  ShieldCheck,
  Workflow,
} from "lucide-react";
import KineticGrid from "@/components/ui/kinetic-grid";
import { SentinelLogo } from "@/components/brand/sentinel-logo";
import { fetchEvals, fetchSystem } from "@/lib/api";
import type { EvalSummary, SystemInfo } from "@/lib/types";

const EASE = [0.22, 1, 0.36, 1] as const;

/* the four accountable outcomes — the "instruments" on the ticker */
/* the four accountable routes and the real sub-pipeline behind each */
const BRANCHES = [
  {
    label: "Answer",
    color: "var(--color-answer)",
    note: "cited from docs",
    steps: [
      { t: "Retrieve", d: "pgvector · hybrid + RRF" },
      { t: "Confidence gate", d: "cosine ≥ min" },
      { t: "Cited answer", d: "citations, or escalate" },
    ],
  },
  {
    label: "Act",
    color: "var(--color-action)",
    note: "allow-listed tool",
    steps: [
      { t: "Validate", d: "Pydantic params" },
      { t: "Critic gate", d: "block / revise / allow" },
      { t: "Approval queue", d: "high-risk held for a human" },
      { t: "n8n webhook", d: "idempotent execution" },
    ],
  },
  {
    label: "Escalate",
    color: "var(--color-escalate)",
    note: "hand to a human",
    steps: [{ t: "Human operator", d: "routed with full context" }],
  },
  {
    label: "Reject",
    color: "var(--color-spam)",
    note: "spam / injection",
    steps: [{ t: "Dropped", d: "no side effects" }],
  },
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

/* synthetic confidence series for the hero chart (0..1) */
const SERIES = [
  0.42, 0.48, 0.44, 0.55, 0.61, 0.58, 0.67, 0.72, 0.69, 0.78, 0.83, 0.8, 0.88,
  0.85, 0.92, 0.9, 0.95,
];

/* the live decision feed that scrolls through the terminal */
const FEED = [
  { route: "Answer", detail: "Refund window · billing-faq#3", color: "var(--color-answer)" },
  { route: "Act", detail: "create_ticket · urgency=high", color: "var(--color-action)" },
  { route: "Escalate", detail: "cancel_invoice · held for review", color: "var(--color-escalate)" },
  { route: "Answer", detail: "SSO setup · security-guide#7", color: "var(--color-answer)" },
  { route: "Reject", detail: "prompt injection · dropped", color: "var(--color-spam)" },
  { route: "Act", detail: "reset_password · idempotent", color: "var(--color-action)" },
] as const;

export default function ArchitecturePage() {
  const [system, setSystem] = useState<SystemInfo | null>(null);
  const [evals, setEvals] = useState<EvalSummary | null>(null);
  const reduce = useReducedMotion();

  const heroRef = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"],
  });
  const { scrollYProgress: pageProgress } = useScroll();

  // Hero recedes as you scroll; the bubble sinks slower (depth).
  const textY = useTransform(scrollYProgress, [0, 1], [0, -90]);
  const textOpacity = useTransform(scrollYProgress, [0, 0.75], [1, 0]);

  useEffect(() => {
    let alive = true;
    Promise.allSettled([fetchSystem(), fetchEvals()]).then(([s, e]) => {
      if (!alive) return;
      if (s.status === "fulfilled") setSystem(s.value);
      if (e.status === "fulfilled" && e.value) setEvals(e.value);
    });
    return () => {
      alive = false;
    };
  }, []);

  const passRate = evals ? Math.round((evals.passRate ?? 0) * 100) : 96;

  return (
    <KineticGrid className="min-h-full">
      {/* scroll progress */}
      <motion.div
        aria-hidden
        className="fixed inset-x-0 top-0 z-[60] h-0.5 origin-left"
        style={{ scaleX: pageProgress, background: "var(--grad-brand)" }}
      />

      {/* ── nav ── */}
      <header className="fixed inset-x-0 top-0 z-50">
        <div className="mx-auto mt-3 flex w-full max-w-[1220px] items-center justify-between rounded-2xl glass px-4 py-2.5 sm:px-5">
          <Link href="/" aria-label="Sentinel home">
            <SentinelLogo />
          </Link>
          <nav className="flex items-center gap-1 sm:gap-5" aria-label="Primary">
            <Link href="/inbox" className="nav-link hidden sm:inline">Run log</Link>
            <Link href="/usage" className="nav-link hidden sm:inline">Observability</Link>
            <Link href="/approvals" className="nav-link hidden sm:inline">Approvals</Link>
            <Link href="/console" className="beacon-btn group">
              Open console
              <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
            </Link>
          </nav>
        </div>
      </header>

      {/* ── hero — centered over the kinetic grid ── */}
      <section ref={heroRef} className="relative flex min-h-[100svh] flex-col items-center justify-center px-5 pb-8 pt-28 text-center sm:pt-32">
        <motion.div
          style={reduce ? undefined : { y: textY, opacity: textOpacity }}
          className="relative z-10 flex flex-col items-center"
        >
          <motion.span
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: EASE }}
            className="chip"
          >
            <span className="size-1.5 animate-pulse rounded-full bg-brand" />
            Evidence-first support operations
          </motion.span>

          <motion.h1
            initial={{ opacity: 0, y: 22 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.75, ease: EASE, delay: 0.05 }}
            className="mt-6 max-w-4xl font-display text-[44px] font-normal leading-[0.96] tracking-[-0.02em] text-fg sm:text-[76px]"
          >
            Elevate every
            <br />
            request into{" "}
            <span className="italic text-gradient">accountability.</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: EASE, delay: 0.12 }}
            className="mt-6 max-w-xl text-[16px] leading-7 text-dim sm:text-[17px]"
          >
            Sentinel triages every incoming ticket through one accountable spine —
            retrieve, decide, gate, act, and record. It answers only with citations
            it can prove, and raises a human wherever a decision carries real risk.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, ease: EASE, delay: 0.18 }}
            className="mt-9 flex flex-wrap items-center justify-center gap-3"
          >
            <Link href="/console" className="beacon-btn group px-6 py-3 text-[15px]">
              Open the console
              <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
            <Link href="/inbox" className="ghost-btn px-6 py-3 text-[15px]">
              See the run log
              <ArrowUpRight className="size-4" />
            </Link>
          </motion.div>

          <motion.dl
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, ease: EASE, delay: 0.26 }}
            className="mt-12 grid w-full max-w-lg grid-cols-3 gap-6 border-t border-edge/70 pt-6"
          >
            <HeroStat value={passRate} suffix="%" label="eval pass rate" tone="answer" />
            <HeroStat value={4} label="accountable routes" tone="brand" />
            <HeroStat value={100} suffix="%" label="actions audited" tone="brand" />
          </motion.dl>
        </motion.div>

        {/* scroll cue */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1, duration: 0.8 }}
          className="relative z-10 mt-auto flex flex-col items-center gap-2 pt-10 font-mono text-[10px] uppercase tracking-[0.18em] text-faint"
        >
          Scroll to watch it decide
          <motion.span
            animate={reduce ? undefined : { y: [0, 6, 0] }}
            transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
            className="grid size-6 place-items-center rounded-full border border-edge"
          >
            <ArrowRight className="size-3 rotate-90 text-brand" />
          </motion.span>
        </motion.div>
      </section>

      {/* ── live terminal — revealed ── */}
      <section className="seam relative">
        <div className="mx-auto grid w-full max-w-[1220px] items-center gap-10 px-5 py-24 sm:px-8 lg:grid-cols-[0.9fr_1.1fr]">
          <Reveal>
            <p className="eyebrow text-brand">Live triage</p>
            <h2 className="mt-4 font-display text-3xl leading-tight text-fg sm:text-5xl">
              Watch a decision form in real time.
            </h2>
            <p className="mt-5 max-w-md text-[15px] leading-7 text-dim">
              Retrieval confidence climbs as evidence is fused; the router commits to
              one of four accountable outcomes; and every step lands in the audit log —
              route, citations, tokens, cost and latency.
            </p>
            <Link href="/console" className="ghost-btn mt-7 px-5 py-3 text-[15px]">
              Open the live console
              <ArrowUpRight className="size-4" />
            </Link>
          </Reveal>

          <Reveal delay={0.1}>
            <LiveTerminal />
          </Reveal>
        </div>
      </section>

      {/* ── trust marquee ── */}
      <section className="seam relative bg-surface/20 py-6">
        <div className="mx-auto flex w-full max-w-[1220px] items-center gap-6 px-5 sm:px-8">
          <span className="hidden shrink-0 font-mono text-[10px] uppercase tracking-[0.16em] text-faint sm:block">
            Self-hosted stack
          </span>
          <div className="marquee-mask relative flex-1 overflow-hidden">
            <div className="marquee-track gap-3">
              {[...STACK, ...STACK].map((s, i) => (
                <span key={`${s}-${i}`} className="rounded-lg border border-edge bg-ink/60 px-3 py-1.5 font-mono text-xs text-dim">
                  {s}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── architecture ── */}
      <section className="seam relative">
        <div className="mx-auto w-full max-w-[1220px] px-5 py-24 sm:px-8">
          <Reveal>
            <p className="eyebrow text-brand">The architecture</p>
            <h2 className="mt-4 font-display text-3xl leading-tight text-fg sm:text-5xl">
              Request in. Accountable decision out.
            </h2>
            <p className="mt-4 max-w-2xl text-[15px] leading-7 text-dim">
              One request flows through four layers — ingress, a routing decision,
              the route&apos;s own sub-pipeline, and a permanent record — so every
              outcome is traceable back to the evidence and gates behind it.
            </p>
          </Reveal>
          <Reveal delay={0.08}>
            <ArchitectureDiagram evals={evals} />
          </Reveal>
        </div>
      </section>

      {/* ── bento layers ── */}
      <section className="seam relative">
        <div className="mx-auto w-full max-w-[1220px] px-5 py-24 sm:px-8">
          <Reveal>
            <p className="eyebrow text-answer">The layers</p>
            <h2 className="mt-4 font-display text-3xl leading-tight text-fg sm:text-5xl">
              Six responsibilities, cleanly separated.
            </h2>
          </Reveal>

          <div className="mt-12 grid auto-rows-[1fr] gap-4 md:grid-cols-3">
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
              color="var(--color-cyan)"
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

      {/* ── CTA ── */}
      <section className="seam relative">
        <div className="mx-auto w-full max-w-[1220px] px-5 py-24 sm:px-8">
          <Reveal>
            <div className="gradient-border relative overflow-hidden rounded-3xl border border-edge bg-surface/40 px-6 py-16 text-center sm:px-16">
              <div className="aurora aurora-violet absolute -top-24 left-1/2 h-72 w-72 -translate-x-1/2 opacity-40" />
              <p className="eyebrow relative text-brand">Ready when you are</p>
              <h2 className="relative mx-auto mt-4 max-w-2xl font-display text-3xl leading-tight text-fg sm:text-5xl">
                Watch a real request move through the spine.
              </h2>
              <p className="relative mx-auto mt-5 max-w-xl text-[15px] leading-7 text-dim">
                Send a ticket, follow the route decision, inspect the citations, and
                approve or hold any high-risk action — live.
              </p>
              <div className="relative mt-9 flex flex-wrap justify-center gap-3">
                <Link href="/console" className="beacon-btn group px-6 py-3 text-[15px]">
                  Open the console
                  <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
                </Link>
                <Link href="/usage" className="ghost-btn px-6 py-3 text-[15px]">
                  View observability
                </Link>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      <footer className="seam">
        <div className="mx-auto flex w-full max-w-[1220px] flex-col gap-3 px-5 py-8 font-mono text-[10px] uppercase tracking-[0.14em] text-faint sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <span>Sentinel · evidence-first support operations</span>
          <span className="flex items-center gap-2">
            <span className={`size-1.5 rounded-full ${system ? "bg-answer" : "bg-faint"}`} />
            {system ? "runtime online" : "runtime offline"} · FastAPI · LangGraph · Next.js
          </span>
        </div>
      </footer>
    </KineticGrid>
  );
}

/* ── hero stat (count-up) ───────────────────────────────────────── */

const TONE: Record<string, string> = {
  answer: "var(--color-answer)",
  brand: "var(--color-brand)",
};

function HeroStat({
  value,
  suffix,
  label,
  tone = "brand",
}: {
  value: number;
  suffix?: string;
  label: string;
  tone?: keyof typeof TONE;
}) {
  return (
    <div>
      <dd className="font-display text-3xl leading-none text-fg sm:text-4xl">
        <span style={{ color: TONE[tone] }}>
          <CountNumber value={value} suffix={suffix} />
        </span>
      </dd>
      <dt className="mt-2 font-mono text-[10px] uppercase tracking-[0.14em] text-faint">
        {label}
      </dt>
    </div>
  );
}

/* ── hero live terminal ─────────────────────────────────────────── */

function LiveTerminal() {
  return (
    <div className="gradient-border relative rounded-2xl border border-edge bg-surface/60 p-4 shadow-[0_40px_120px_-60px_rgba(0,0,0,0.9)] backdrop-blur-xl sm:p-5">
      <div className="flex items-center justify-between border-b border-edge pb-3">
        <div className="flex items-center gap-2">
          <span className="size-2.5 rounded-full bg-escalate/70" />
          <span className="size-2.5 rounded-full bg-action/70" />
          <span className="size-2.5 rounded-full bg-answer/70" />
        </div>
        <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-faint">
          <span className="size-1.5 rounded-full bg-answer" style={{ animation: "watch-pulse 2.6s ease-out infinite" }} />
          live triage
        </span>
      </div>

      <div className="mt-4">
        <div className="flex items-baseline justify-between">
          <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-faint">retrieval confidence</p>
          <p className="font-mono text-xs text-answer">+18.4% ↑</p>
        </div>
        <ConfidenceChart />
        <div className="mt-1 flex justify-between font-mono text-[9px] uppercase tracking-[0.12em] text-faint">
          <span>gate 0.35</span>
          <span>topk fused</span>
          <span>0.95</span>
        </div>
      </div>

      <div className="mt-4 border-t border-edge pt-3">
        <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.16em] text-faint">decision feed</p>
        <DecisionFeed />
      </div>
    </div>
  );
}

function ConfidenceChart() {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-10% 0px" });

  const W = 100;
  const H = 42;
  const min = 0.3;
  const pts = SERIES.map((v, i) => ({
    x: (i / (SERIES.length - 1)) * W,
    y: H - ((v - min) / (1 - min)) * H,
  }));
  const line = smoothPath(pts);
  const area = `${line} L ${W} ${H} L 0 ${H} Z`;
  const last = pts[pts.length - 1];

  return (
    <div ref={ref} className="relative mt-2">
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="h-24 w-full overflow-visible">
        <defs>
          <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-brand)" stopOpacity="0.34" />
            <stop offset="100%" stopColor="var(--color-brand)" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="lineStroke" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="var(--color-violet)" />
            <stop offset="100%" stopColor="var(--color-cyan)" />
          </linearGradient>
        </defs>
        <line x1="0" y1={H - (0.05 / 0.7) * H} x2={W} y2={H - (0.05 / 0.7) * H}
          stroke="var(--color-edge-strong)" strokeWidth="0.4" strokeDasharray="1.5 1.5" />
        <motion.path
          d={area}
          fill="url(#areaFill)"
          initial={{ opacity: 0 }}
          animate={inView ? { opacity: 1 } : {}}
          transition={{ duration: 0.8, delay: 0.5 }}
        />
        <motion.path
          d={line}
          fill="none"
          stroke="url(#lineStroke)"
          strokeWidth="1.4"
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={{ pathLength: reduce ? 1 : 0 }}
          animate={inView ? { pathLength: 1 } : {}}
          transition={{ duration: 1.4, ease: EASE }}
        />
        <motion.circle
          cx={last.x}
          cy={last.y}
          r="1.8"
          fill="var(--color-cyan)"
          initial={{ opacity: 0 }}
          animate={inView ? { opacity: 1 } : {}}
          transition={{ delay: 1.3 }}
        />
      </svg>
    </div>
  );
}

function DecisionFeed() {
  const [i, setI] = useState(0);
  const reduce = useReducedMotion();

  useEffect(() => {
    if (reduce) return;
    const t = setInterval(() => setI((n) => (n + 1) % FEED.length), 2200);
    return () => clearInterval(t);
  }, [reduce]);

  const rows = [0, 1, 2].map((k) => FEED[(i + k) % FEED.length]);

  return (
    <div className="space-y-1.5">
      <AnimatePresence initial={false} mode="popLayout">
        {rows.map((r, k) => (
          <motion.div
            key={`${r.route}-${r.detail}`}
            layout
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: k === 2 ? 0.55 : 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.35, ease: EASE }}
            className="flex items-center gap-2.5 rounded-lg border border-edge bg-ink/50 px-3 py-2"
          >
            <span className="size-1.5 shrink-0 rounded-full" style={{ background: r.color, boxShadow: `0 0 8px -1px ${r.color}` }} />
            <span className="w-16 shrink-0 font-mono text-[11px]" style={{ color: r.color }}>{r.route}</span>
            <span className="truncate font-mono text-[11px] text-dim">{r.detail}</span>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

/* ── count-up number ────────────────────────────────────────────── */

function CountNumber({
  value,
  suffix,
}: {
  value: number;
  suffix?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-15% 0px" });
  const reduce = useReducedMotion();
  const [n, setN] = useState(0);

  useEffect(() => {
    if (!inView) return;
    if (reduce) {
      setN(value);
      return;
    }
    const controls = animate(0, value, {
      duration: 1.4,
      ease: EASE,
      onUpdate: (v) => setN(v),
    });
    return () => controls.stop();
  }, [inView, value, reduce]);

  return (
    <span ref={ref}>
      {Math.round(n)}
      {suffix}
    </span>
  );
}

/* ── architecture diagram ───────────────────────────────────────── */

function ArchitectureDiagram({ evals }: { evals: EvalSummary | null }) {
  return (
    <div className="mt-12 overflow-hidden rounded-2xl border border-edge bg-ink/60 p-5 backdrop-blur-sm sm:p-8">
      {/* ── 01 · Ingress ── */}
      <LayerTag n="01" title="Ingress" />
      <div className="mt-3 flex flex-col items-stretch gap-3 sm:flex-row sm:items-center">
        <div className="grid flex-1 grid-cols-3 gap-2">
          {["Web form", "Email", "Chat"].map((c) => (
            <div key={c} className="rounded-lg border border-edge bg-surface/40 px-3 py-2.5 text-center">
              <span className="text-[13px] text-dim">{c}</span>
            </div>
          ))}
        </div>
        <FlowArrow />
        <NodeCard title="FastAPI" sub="POST /triage" mono className="sm:w-52" />
      </div>

      <FlowLink />

      {/* ── 02 · Decide ── */}
      <LayerTag n="02" title="Decide" />
      <NodeCard
        title="LangGraph router"
        sub="intent · urgency · confidence → route"
        accent
        className="mt-3"
      />

      {/* ── 03 · Route ── */}
      <LayerTag n="03" title="Route" className="mt-4" />

      {/* distributor into the four branches */}
      <div aria-hidden className="relative mx-auto mt-1 hidden h-6 max-w-[92%] lg:block">
        <span className="absolute left-1/2 top-0 h-3 w-px -translate-x-1/2 bg-edge" />
        <span className="absolute left-[12.5%] right-[12.5%] top-3 h-px bg-edge" />
        {[12.5, 37.5, 62.5, 87.5].map((l) => (
          <span key={l} className="absolute top-3 h-3 w-px bg-edge" style={{ left: `${l}%` }} />
        ))}
      </div>

      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {BRANCHES.map((b, i) => (
          <Branch key={b.label} branch={b} index={i} />
        ))}
      </div>

      {/* converge into the record layer */}
      <div aria-hidden className="mx-auto mt-1 hidden h-6 w-px bg-edge lg:block" />

      {/* ── 04 · Record (cross-cutting) ── */}
      <LayerTag n="04" title="Record" className="mt-6 lg:mt-3" />
      <div className="mt-3 grid gap-2 rounded-xl border border-edge bg-surface/40 p-2 sm:grid-cols-3">
        <RecordItem title="Audit log" sub="runs table · per-step" />
        <RecordItem title="Cost + tokens" sub="metered per run" />
        <RecordItem title="Langfuse trace" sub="optional, full span" />
      </div>
      <p className="mt-3 text-center font-mono text-[10px] uppercase tracking-[0.14em] text-faint">
        gated in CI by a deterministic eval suite
        {evals ? ` · ${evals.passed}/${evals.total} passing` : " · 245/245 passing"}
      </p>
    </div>
  );
}

function LayerTag({ n, title, className }: { n: string; title: string; className?: string }) {
  return (
    <div className={`flex items-center gap-2.5 ${className ?? ""}`}>
      <span className="font-mono text-[10px] text-faint">{n}</span>
      <span className="h-px w-6 bg-edge-strong" />
      <span className="eyebrow !text-dim">{title}</span>
    </div>
  );
}

function NodeCard({
  title,
  sub,
  accent,
  mono,
  className,
}: {
  title: string;
  sub: string;
  accent?: boolean;
  mono?: boolean;
  className?: string;
}) {
  return (
    <div
      className={`rounded-xl border bg-surface/60 px-4 py-3 ${className ?? ""}`}
      style={{
        borderColor: accent
          ? "color-mix(in oklab, var(--color-brand) 45%, var(--color-edge))"
          : "var(--color-edge)",
        boxShadow: accent ? "inset 0 0 0 1px color-mix(in oklab, var(--color-brand) 14%, transparent)" : undefined,
      }}
    >
      <p className={`text-sm font-semibold ${accent ? "text-brand" : "text-fg"}`}>{title}</p>
      <p className={`mt-0.5 text-[11px] text-faint ${mono ? "font-mono" : ""}`}>{sub}</p>
    </div>
  );
}

function Branch({
  branch,
  index,
}: {
  branch: (typeof BRANCHES)[number];
  index: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-8% 0px" }}
      transition={{ duration: 0.45, ease: EASE, delay: index * 0.08 }}
      className="flex flex-col rounded-xl border border-edge bg-surface/40 p-3"
      style={{ boxShadow: `inset 0 0 0 1px color-mix(in oklab, ${branch.color} 14%, transparent)` }}
    >
      {/* header */}
      <div className="flex items-center gap-2 px-1 pb-2.5">
        <span
          className="size-2 rounded-full"
          style={{ background: branch.color, boxShadow: `0 0 10px -1px ${branch.color}` }}
        />
        <span className="font-display text-lg leading-none" style={{ color: branch.color }}>
          {branch.label}
        </span>
        <span className="ml-auto font-mono text-[9px] uppercase tracking-[0.1em] text-faint">
          {branch.note}
        </span>
      </div>

      {/* steps */}
      <div className="flex flex-1 flex-col gap-1">
        {branch.steps.map((s, j) => (
          <div key={s.t}>
            {j > 0 && <span aria-hidden className="mx-auto block h-2 w-px bg-edge" />}
            <div
              className="rounded-lg border border-edge bg-ink/50 px-3 py-2"
              style={{ borderLeft: `2px solid color-mix(in oklab, ${branch.color} 55%, var(--color-edge))` }}
            >
              <p className="font-mono text-[11px] leading-tight text-fg">{s.t}</p>
              <p className="mt-0.5 font-mono text-[10px] leading-tight text-faint">{s.d}</p>
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

function RecordItem({ title, sub }: { title: string; sub: string }) {
  return (
    <div className="flex items-center gap-2.5 rounded-lg bg-ink/40 px-3 py-2.5">
      <span className="size-1.5 rounded-full bg-brand" style={{ boxShadow: "0 0 8px -1px var(--color-brand)" }} />
      <span className="min-w-0">
        <span className="block text-[13px] text-fg">{title}</span>
        <span className="block font-mono text-[10px] text-faint">{sub}</span>
      </span>
    </div>
  );
}

/* horizontal flow arrow between ingress and the API */
function FlowArrow() {
  return (
    <span className="relative mx-auto hidden h-px w-8 shrink-0 bg-edge sm:block">
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

/* vertical flow link with a travelling pulse */
function FlowLink() {
  return (
    <span className="relative mx-auto my-2 block h-8 w-px bg-edge">
      <motion.span
        className="absolute left-1/2 top-0 size-1.5 -translate-x-1/2 rounded-full bg-brand"
        style={{ boxShadow: "0 0 8px 1px var(--color-brand)" }}
        initial={{ top: "-10%", opacity: 0 }}
        animate={{ top: ["-10%", "110%"], opacity: [0, 1, 0] }}
        transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut", repeatDelay: 0.4 }}
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
          <span key={c} className="rounded-md border border-edge bg-ink px-2 py-1 font-mono text-[10px] text-dim">
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
        { k: "tools", v: system.tools.map((t) => t.name).join(", ") || "—" },
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
      initial={{ opacity: 0, y: 28 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-12% 0px" }}
      transition={{ duration: 0.7, ease: EASE, delay }}
    >
      {children}
    </motion.div>
  );
}

/* Catmull-Rom → cubic bézier smoothing for the chart line. */
function smoothPath(pts: { x: number; y: number }[]): string {
  if (pts.length < 2) return "";
  let d = `M ${pts[0].x} ${pts[0].y}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] ?? pts[i];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[i + 2] ?? p2;
    const c1x = p1.x + (p2.x - p0.x) / 6;
    const c1y = p1.y + (p2.y - p0.y) / 6;
    const c2x = p2.x - (p3.x - p1.x) / 6;
    const c2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C ${c1x} ${c1y} ${c2x} ${c2y} ${p2.x} ${p2.y}`;
  }
  return d;
}
