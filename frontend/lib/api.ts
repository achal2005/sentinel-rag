import type { TriageResult } from "./types";

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
