import { NextResponse } from "next/server";

const API = process.env.SENTINEL_API_URL ?? "http://localhost:8000";

export async function GET() {
  try {
    const upstream = await fetch(`${API}/health`, { cache: "no-store" });
    return NextResponse.json({ ok: upstream.ok }, { status: upstream.ok ? 200 : 502 });
  } catch {
    return NextResponse.json({ ok: false }, { status: 502 });
  }
}
