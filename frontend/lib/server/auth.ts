/**
 * Server-only helper. When BASIC_AUTH_USER/PASS are configured, the Next.js
 * proxy routes authenticate to the FastAPI backend with the same credentials the
 * edge middleware requires from the browser. Empty when unset (local dev).
 *
 * Never import this from a client component — it reads server-side secrets.
 */
export function backendAuthHeader(): Record<string, string> {
  const user = process.env.BASIC_AUTH_USER;
  const pass = process.env.BASIC_AUTH_PASS;
  if (!user || !pass) return {};
  const token = Buffer.from(`${user}:${pass}`).toString("base64");
  return { authorization: `Basic ${token}` };
}
