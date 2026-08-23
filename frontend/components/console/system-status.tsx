"use client";

import { useEffect, useState } from "react";
import { checkHealth } from "@/lib/api";

type Health = "checking" | "online" | "offline";

export function SystemStatus() {
  const [health, setHealth] = useState<Health>("checking");

  useEffect(() => {
    let alive = true;
    const ping = async () => {
      const ok = await checkHealth();
      if (alive) setHealth(ok ? "online" : "offline");
    };
    ping();
    const t = setInterval(ping, 15000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  const color =
    health === "online"
      ? "var(--color-answer)"
      : health === "offline"
        ? "var(--color-escalate)"
        : "var(--color-faint)";
  const label =
    health === "online" ? "API online" : health === "offline" ? "API offline" : "checking…";

  return (
    <span className="inline-flex items-center gap-2 font-mono text-xs text-dim">
      <span
        className="size-2 rounded-full"
        style={{
          background: color,
          boxShadow: health === "online" ? `0 0 10px ${color}` : "none",
          animation: health === "checking" ? "fade 1s ease-in-out infinite alternate" : "none",
        }}
      />
      {label}
    </span>
  );
}
