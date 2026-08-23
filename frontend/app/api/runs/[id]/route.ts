import { NextResponse } from "next/server";
import { backendAuthHeader } from "@/lib/server/auth";

const API = process.env.SENTINEL_API_URL ?? "http://localhost:8000";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  try {
    const upstream = await fetch(`${API}/runs/${encodeURIComponent(id)}`, {
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
