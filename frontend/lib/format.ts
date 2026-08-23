/** Compact relative time: accepts epoch ms or an ISO string. */
export function ago(input: number | string): string {
  const t = typeof input === "number" ? input : new Date(input).getTime();
  const s = Math.max(0, (Date.now() - t) / 1000);
  if (s < 45) return "just now";
  if (s < 60) return `${Math.floor(s)}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}
