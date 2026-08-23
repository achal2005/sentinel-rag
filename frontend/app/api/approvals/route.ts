import { NextResponse } from "next/server";
import { backendAuthHeader } from "@/lib/server/auth";

const API = process.env.SENTINEL_API_URL ?? "http://localhost:8000";

// GET /api/approvals?status=pending -> backend /approvals
export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const status = searchParams.get("status") ?? "pending";
  try {
    const upstream = await fetch(`${API}/approvals?status=${encodeURIComponent(status)}`, {
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
