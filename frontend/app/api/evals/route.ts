import { NextResponse } from "next/server";
import { readFile } from "node:fs/promises";
import path from "node:path";

/**
 * Serves the REAL evaluation summary from the repo's latest report
 * (evals/reports/latest.json), so the console shows genuine numbers — no
 * hand-typed metrics. Next dev runs with cwd = frontend/, so the report lives
 * one level up. Falls back to a couple of candidate paths to be robust.
 */

// Friendly labels + display order for the capabilities we surface.
const CAPABILITY_LABELS: Record<string, string> = {
  // Deterministic citation checks verify required/present/source-ID behavior.
  // "Citation faithfulness" is reserved for the separate semantic judge.
  citations: "Citation checks",
  adversarial_safety: "Adversarial safety",
  approval_safety: "Approval safety",
  routing: "Routing accuracy",
  retrieval: "Retrieval",
  reliability_fallback: "Reliability / fallback",
  tool_selection: "Tool selection",
  tool_parameter_values: "Tool parameters",
  escalation: "Escalation",
  audit_logging: "Audit logging",
  intent: "Intent",
  multi_turn: "Multi-turn",
};
const ORDER = Object.keys(CAPABILITY_LABELS);

async function readReport(): Promise<string | null> {
  const candidates = [
    path.join(process.cwd(), "..", "evals", "reports", "latest.json"),
    path.join(process.cwd(), "evals", "reports", "latest.json"),
  ];
  for (const p of candidates) {
    try {
      return await readFile(/* turbopackIgnore: true */ p, "utf8");
    } catch {
      /* try next */
    }
  }
  return null;
}

export async function GET() {
  const raw = await readReport();
  if (!raw) {
    return NextResponse.json({ detail: "No eval report found" }, { status: 404 });
  }

  let report: Record<string, unknown>;
  try {
    report = JSON.parse(raw);
  } catch {
    return NextResponse.json({ detail: "Eval report is not valid JSON" }, { status: 500 });
  }

  const s = (report.summary ?? {}) as Record<string, unknown>;
  const metrics = (s.metrics ?? {}) as Record<
    string,
    { passed?: number; denominator?: number; rate?: number }
  >;
  const dataset = (s.dataset ?? {}) as Record<string, unknown>;

  const capabilities = ORDER.filter((k) => metrics[k])
    .map((k) => ({
      key: k,
      label: CAPABILITY_LABELS[k],
      passed: metrics[k].passed ?? 0,
      denominator: metrics[k].denominator ?? 0,
      rate: metrics[k].rate ?? 0,
    }));

  return NextResponse.json(
    {
      generatedAt: s.generated_at ?? null,
      total: s.total ?? 0,
      passed: s.passed ?? 0,
      failed: s.failed ?? 0,
      passRate: s.overall_pass_rate ?? 0,
      criticalPassed: s.critical_policy_passed ?? null,
      dataset: dataset.dataset ?? null,
      version: dataset.version ?? null,
      totalCases: dataset.total_cases ?? null,
      semanticJudge: dataset.semantic_judge ?? null,
      tools: (dataset.registered_tools ?? []) as string[],
      capabilities,
    },
    { headers: { "cache-control": "no-store" } },
  );
}
