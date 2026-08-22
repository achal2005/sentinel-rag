import type {
  ApprovalActionResult,
  ApprovalItem,
  EvalSummary,
  RunDetail,
  RunRow,
  SystemInfo,
  TriageResult,
  UsageStats,
} from "./types";

/**
 * The console talks to same-origin Next route handlers (app/api/*), which proxy
 * to the FastAPI backend. That keeps the backend URL server-side and sidesteps
 * CORS entirely.
 */

export async function triage(query: string): Promise<TriageResult> {
  const res = await fetch("/api/triage", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ query, channel: "web_form" }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(
      res.status === 502
        ? "Can't reach the Sentinel API."
        : `Triage failed (${res.status}). ${detail}`.trim(),
    );
  }
  return res.json();
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch("/api/health", { cache: "no-store" });
    return res.ok;
  } catch {
    return false;
  }
}

/** Non-secret runtime facts: configured models, retrieval gate, and tool registry. */
export async function fetchSystem(): Promise<SystemInfo> {
  const res = await fetch("/api/system", { cache: "no-store" });
  if (!res.ok) {
    throw new Error(
      res.status === 502 ? "Can't reach the Sentinel API." : `Failed to load runtime (${res.status}).`,
    );
  }
  return res.json();
}

/** The real evaluation summary (from evals/reports/latest.json). */
export async function fetchEvals(): Promise<EvalSummary | null> {
  try {
    const res = await fetch("/api/evals", { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

/** Recent triage runs — the Inbox, from the real `runs` table. */
export async function fetchRuns(limit = 30): Promise<RunRow[]> {
  const res = await fetch(`/api/runs?limit=${limit}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(
      res.status === 502 ? "Can't reach the Sentinel API." : `Failed to load inbox (${res.status}).`,
    );
  }
  return res.json();
}

/** One run's full trace (row + citations + audit steps). */
export async function fetchRun(id: string | number): Promise<RunDetail> {
  const res = await fetch(`/api/runs/${id}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(
      res.status === 404 ? "That request wasn't found." : `Failed to load trace (${res.status}).`,
    );
  }
  return res.json();
}

/** Aggregate usage + cost stats for the dashboard. */
export async function fetchStats(): Promise<UsageStats> {
  const res = await fetch("/api/stats", { cache: "no-store" });
  if (!res.ok) {
    throw new Error(
      res.status === 502 ? "Can't reach the Sentinel API." : `Failed to load stats (${res.status}).`,
    );
  }
  return res.json();
}

/** Read the approval queue (defaults to pending items awaiting a decision). */
export async function fetchApprovals(
  status: "pending" | "all" = "pending",
): Promise<ApprovalItem[]> {
  const res = await fetch(`/api/approvals?status=${status}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(
      res.status === 502 ? "Can't reach the Sentinel API." : `Failed to load queue (${res.status}).`,
    );
  }
  return res.json();
}

/**
 * Approve or reject a queued action. Approving triggers the underlying tool
 * (fires the n8n webhook); rejecting just closes the item.
 */
export async function decideApproval(
  id: number,
  action: "approve" | "reject",
): Promise<ApprovalActionResult> {
  const res = await fetch(`/api/approvals/${id}/${action}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ decided_by: "operator" }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(
      res.status === 409
        ? "That item was already decided."
        : `Could not ${action} (${res.status}). ${detail}`.trim(),
    );
  }
  return res.json();
}
