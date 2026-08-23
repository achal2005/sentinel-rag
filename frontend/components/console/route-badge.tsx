import { ROUTES, routeColor } from "@/lib/routes";
import type { RouteKey } from "@/lib/types";

export function RouteBadge({ route }: { route: RouteKey }) {
  const meta = ROUTES[route];
  const c = routeColor(route);
  return (
    <span
      className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wider"
      style={{
        color: c,
        background: `color-mix(in oklab, ${c} 12%, transparent)`,
        boxShadow: `inset 0 0 0 1px color-mix(in oklab, ${c} 35%, transparent)`,
      }}
    >
      <span
        className="size-1.5 rounded-full"
        style={{ background: c, boxShadow: `0 0 8px ${c}` }}
      />
      {meta.label}
    </span>
  );
}
