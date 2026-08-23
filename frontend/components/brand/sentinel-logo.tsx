import * as React from "react";

/**
 * Sentinel brand mark — "the aperture beacon".
 * A luminous node (the signal under watch) inside an open aperture ring (the
 * sentinel keeping watch; the gap reads as a scanning aperture, not a target).
 * Monoline and themeable: the ring inherits `currentColor`; the node uses the
 * beacon accent. Crisp from 16px to hero size.
 */
export function SentinelMark({
  className,
  node = "var(--color-brand)",
}: {
  className?: string;
  node?: string;
}) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden>
      {/* aperture ring, with a single watch-gap */}
      <circle
        cx="12"
        cy="12"
        r="8.4"
        fill="none"
        stroke="currentColor"
        strokeOpacity="0.55"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeDasharray="40 13"
        transform="rotate(-74 12 12)"
      />
      {/* faint sweep from the node toward the aperture */}
      <path
        d="M12 12 L18.1 6.6"
        stroke="currentColor"
        strokeOpacity="0.28"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      {/* beacon node */}
      <circle cx="12" cy="12" r="2.5" fill={node} />
    </svg>
  );
}

/**
 * Full lockup: the mark in a tile beside the wordmark and a mono tagline.
 * Pass `tagline={null}` for a compact version.
 */
export function SentinelLogo({
  className,
  tagline = "evidence desk",
}: {
  className?: string;
  tagline?: string | null;
}) {
  return (
    <span className={`inline-flex items-center gap-2.5 ${className ?? ""}`}>
      <span className="grid size-8 place-items-center rounded-lg border border-edge bg-surface text-brand">
        <SentinelMark className="size-5" />
      </span>
      <span className="flex flex-col leading-none">
        <span className="font-display text-lg tracking-[-0.01em] text-fg">
          Sentinel
        </span>
        {tagline && (
          <span className="mt-0.5 font-mono text-[8px] uppercase tracking-[0.2em] text-faint">
            {tagline}
          </span>
        )}
      </span>
    </span>
  );
}
