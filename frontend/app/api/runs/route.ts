import { NextResponse } from "next/server";
import { backendAuthHeader } from "@/lib/server/auth";

const API = process.env.SENTINEL_API_URL ?? "http://localhost:8000";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const limit = searchParams.get("limit") ?? "30";
  try {
    const upstream = await fetch(`${API}/runs?limit=${encodeURIComponent(limit)}`, {
      cache: "no-store",
      headers: { ...backendAuthHeader() },
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
