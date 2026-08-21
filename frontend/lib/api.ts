import type { ApprovalActionResult, ApprovalItem, TriageResult } from "./types";

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
