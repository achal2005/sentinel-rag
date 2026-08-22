"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { fetchApprovals } from "@/lib/api";
import { SystemStatus } from "@/components/console/system-status";
import { SentinelMark as BrandMark } from "@/components/brand/sentinel-logo";

/* ---- nav model ------------------------------------------------------- */

type NavItem = {
  href: string;
  label: string;
  icon: (p: { className?: string }) => React.ReactNode;
  match: (path: string) => boolean;
};

const NAV: NavItem[] = [
  { href: "/inbox", label: "Inbox", icon: InboxIcon, match: (p) => p.startsWith("/inbox") || p.startsWith("/requests") },
  { href: "/approvals", label: "Approvals", icon: ShieldIcon, match: (p) => p.startsWith("/approvals") },
  { href: "/usage", label: "Observability", icon: PulseIcon, match: (p) => p.startsWith("/usage") },
  { href: "/console", label: "Live console", icon: ConsoleIcon, match: (p) => p.startsWith("/console") },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [pending, setPending] = useState<number | null>(null);

  // Keep the approvals badge honest — poll the real queue.
  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const rows = await fetchApprovals("pending");
        if (alive) setPending(rows.length);
      } catch {
        if (alive) setPending(null);
      }
    };
    load();
    const t = setInterval(load, 15000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  return (
    <div className="flex min-h-full bg-ink">
      {/* A narrow evidence index: navigation without dashboard chrome. */}
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-edge bg-surface/35 px-5 py-6 lg:flex">
        <Brand />

        <Link
          href="/console"
          className="clay-btn mt-8 inline-flex items-center justify-center gap-2 bg-brand px-3 py-2.5 text-sm font-semibold text-[#041417] focus-visible:outline-none"
        >
          <PlusIcon className="size-4" />
          New request
        </Link>

        <p className="eyebrow mb-3 mt-8 px-3">Evidence desk</p>
        <nav className="flex flex-col gap-1 border-t border-edge pt-2">
          {NAV.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              active={item.match(pathname)}
              badge={item.href === "/approvals" ? pending ?? undefined : undefined}
            />
          ))}
        </nav>

        <div className="mt-auto space-y-3 pt-6">
          <div className="h-px w-full bg-edge" />
          <SystemStatus />
          <p className="font-mono text-[10px] leading-relaxed text-faint">
            High-risk tools remain held until an operator decides.
          </p>
        </div>
      </aside>

      {/* ---- main column ---- */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* A single evidence rule carries the landing-page language into the app. */}
        <div className="beacon-line h-px w-full bg-edge" aria-hidden />

        {/* mobile header + nav */}
        <header className="sticky top-0 z-40 flex flex-col gap-3 border-b border-edge bg-ink/94 px-4 py-3 backdrop-blur-xl lg:hidden">
          <div className="flex items-center justify-between">
            <Brand />
            <SystemStatus />
          </div>
          <nav className="-mx-1 flex items-center gap-1 overflow-x-auto border-t border-edge/70 pt-2">
            {NAV.map((item) => (
              <NavPill
                key={item.href}
                item={item}
                active={item.match(pathname)}
                badge={item.href === "/approvals" ? pending ?? undefined : undefined}
              />
            ))}
          </nav>
        </header>

        <main className="flex-1">{children}</main>
      </div>
    </div>
  );
}

/* ---- brand ----------------------------------------------------------- */

function Brand() {
  return (
    <Link href="/inbox" className="flex items-center gap-2.5 focus-visible:outline-none">
      <SentinelMark />
      <span className="flex flex-col leading-none">
        <span className="font-display text-[15px] font-semibold tracking-tight text-fg">
          Sentinel
        </span>
        <span className="mt-1 inline-flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-[0.16em] text-faint">
          <span
            className="size-1.5 rounded-full bg-answer"
            style={{ animation: "watch-pulse 2.6s ease-out infinite" }}
          />
          evidence desk
        </span>
      </span>
    </Link>
  );
}

function SentinelMark() {
  return (
    <span className="grid size-8 shrink-0 place-items-center rounded-lg border border-edge bg-surface text-brand">
      <BrandMark className="size-5" />
    </span>
  );
}

/* ---- nav pieces ------------------------------------------------------ */

function NavLink({
  item,
  active,
  badge,
}: {
  item: NavItem;
  active: boolean;
  badge?: number;
}) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      className={`group relative flex items-center gap-3 px-3 py-2.5 text-sm transition ${
        active ? "bg-brand/[.055] text-fg" : "text-dim hover:bg-surface-2/60 hover:text-fg"
      }`}
    >
      {/* active marker: a small beacon on the rail */}
      <span
        className={`absolute left-0 top-1/2 h-5 w-px -translate-y-1/2 transition ${
          active ? "bg-brand" : "bg-transparent"
        }`}
      />
      <Icon className={active ? "size-4 text-brand" : "size-4 text-faint group-hover:text-dim"} />
      <span className="flex-1">{item.label}</span>
      {badge !== undefined && badge > 0 && <CountBadge n={badge} />}
    </Link>
  );
}

function NavPill({
  item,
  active,
  badge,
}: {
  item: NavItem;
  active: boolean;
  badge?: number;
}) {
  return (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      className={`inline-flex shrink-0 items-center gap-2 border px-3 py-1.5 text-sm transition ${
        active
          ? "border-edge-strong bg-surface-2 text-fg"
          : "border-transparent text-dim hover:border-edge hover:text-fg"
      }`}
    >
      {item.label}
      {badge !== undefined && badge > 0 && <CountBadge n={badge} />}
    </Link>
  );
}

function CountBadge({ n }: { n: number }) {
  return (
    <span
      className="inline-flex min-w-5 items-center justify-center rounded-full px-1.5 py-0.5 font-mono text-[10px] font-medium leading-none text-action"
      style={{
        background: "color-mix(in oklab, var(--color-action) 14%, transparent)",
        boxShadow: "inset 0 0 0 1px color-mix(in oklab, var(--color-action) 35%, transparent)",
      }}
    >
      {n}
    </span>
  );
}

/* ---- icons (inline; no icon-lib assumptions) ------------------------- */

function InboxIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M22 12h-6l-2 3h-4l-2-3H2" />
      <path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11Z" />
    </svg>
  );
}
function ShieldIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1Z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}
function PulseIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M3 12h4l2 7 4-16 2 9h6" />
    </svg>
  );
}
function ConsoleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <rect x="2.5" y="4" width="19" height="16" rx="2.5" />
      <path d="m6.5 9 3 3-3 3" />
      <path d="M12.5 15h5" />
    </svg>
  );
}
function PlusIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}
