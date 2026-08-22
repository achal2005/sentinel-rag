import { NextResponse, type NextRequest } from "next/server";

/**
 * Edge HTTP Basic auth for the whole console (pages + /api/* proxy routes).
 * Disabled automatically when BASIC_AUTH_USER/PASS are unset, so local dev needs
 * no login. In a public deployment, set both to gate every browser request.
 */
export function middleware(req: NextRequest) {
  const user = process.env.BASIC_AUTH_USER;
  const pass = process.env.BASIC_AUTH_PASS;
  if (!user || !pass) return NextResponse.next();

  const header = req.headers.get("authorization") ?? "";
  const [scheme, encoded] = header.split(" ");
  if (scheme === "Basic" && encoded) {
    try {
      const [u, p] = atob(encoded).split(":");
      if (u === user && p === pass) return NextResponse.next();
    } catch {
      /* fall through to challenge */
    }
  }
  return new NextResponse("Authentication required.", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="Sentinel", charset="UTF-8"' },
  });
}

export const config = {
  // Guard everything except Next internals and the favicon.
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
