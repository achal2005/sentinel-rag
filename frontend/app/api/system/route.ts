import { NextResponse } from "next/server";
import { backendAuthHeader } from "@/lib/server/auth";

const API = process.env.SENTINEL_API_URL ?? "http://localhost:8000";

export async function GET() {
  try {
    const upstream = await fetch(`${API}/system`, {
      cache: "no-store",
      headers: { ...backendAuthHeader() },
    });
    const data = await upstream.text();
    return new NextResponse(data, {
      status: upstream.status,
      headers: {
        "content-type": "application/json",
        "cache-control": "no-store",
      },
    });
  } catch {
    return NextResponse.json({ detail: "Sentinel API unreachable" }, { status: 502 });
  }
}
