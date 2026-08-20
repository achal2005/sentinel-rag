import { NextResponse } from "next/server";

const API = process.env.SENTINEL_API_URL ?? "http://localhost:8000";

export async function POST(req: Request) {
  const body = await req.text();
  try {
    const upstream = await fetch(`${API}/triage`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body,
    });
    const data = await upstream.text();
    return new NextResponse(data, {
      status: upstream.status,
      headers: { "content-type": "application/json" },
    });
  } catch {
    // Backend unreachable — surface a clean 502 the client copy can explain.
    return NextResponse.json(
      { detail: "Sentinel API unreachable" },
      { status: 502 },
    );
  }
}
