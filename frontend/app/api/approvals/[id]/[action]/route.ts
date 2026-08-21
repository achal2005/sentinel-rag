import { NextResponse } from "next/server";

const API = process.env.SENTINEL_API_URL ?? "http://localhost:8000";

// POST /api/approvals/:id/:action  (action = approve | reject)
// Proxies to the backend, which on "approve" triggers the tool's n8n webhook.
export async function POST(
  req: Request,
  { params }: { params: Promise<{ id: string; action: string }> },
) {
  const { id, action } = await params;
  if (action !== "approve" && action !== "reject") {
    return NextResponse.json({ detail: "unknown action" }, { status: 400 });
  }
  const body = await req.text();
  try {
    const upstream = await fetch(`${API}/approvals/${encodeURIComponent(id)}/${action}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: body || "{}",
    });
    const data = await upstream.text();
    return new NextResponse(data, {
      status: upstream.status,
      headers: { "content-type": "application/json" },
    });
  } catch {
    return NextResponse.json({ detail: "Sentinel API unreachable" }, { status: 502 });
  }
}
