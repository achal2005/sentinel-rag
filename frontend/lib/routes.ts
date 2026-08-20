import type { RouteKey } from "./types";

/**
 * The semantic route system. Color here isn't decoration — it encodes the one
 * thing the product decides about every request. Each entry carries its accent
 * (a CSS custom property from globals) plus operator-facing copy.
 */
export interface RouteMeta {
  key: RouteKey;
  label: string;
  /** CSS var name for the accent color, e.g. "--color-answer". */
  cssVar: string;
  /** one-line description of what this outcome means, operator side. */
  blurb: string;
}

export const ROUTES: Record<RouteKey, RouteMeta> = {
  answer: {
    key: "answer",
    label: "Answered",
    cssVar: "--color-answer",
    blurb: "Grounded in the knowledge base, with citations.",
  },
  action: {
    key: "action",
    label: "Action",
    cssVar: "--color-action",
    blurb: "Needs a side effect — queued for human approval.",
  },
  escalate: {
    key: "escalate",
    label: "Escalated",
    cssVar: "--color-escalate",
    blurb: "Handed off to a human.",
  },
  spam: {
    key: "spam",
    label: "Spam",
    cssVar: "--color-spam",
    blurb: "Dropped as junk — not actioned.",
  },
};

export const routeColor = (route: RouteKey) => `var(${ROUTES[route].cssVar})`;

/** Map a route onto the BorderBeam's fixed color presets for the input glow. */
export const routeBeam = (
  route: RouteKey | null,
): "colorful" | "ocean" | "sunset" | "mono" => {
  switch (route) {
    case "answer":
      return "ocean";
    case "action":
    case "escalate":
      return "sunset";
    case "spam":
      return "mono";
    default:
      return "colorful";
  }
};
