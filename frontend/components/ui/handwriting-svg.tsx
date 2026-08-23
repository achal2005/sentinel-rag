"use client";

import { motion, useReducedMotion } from "framer-motion";
import * as opentype from "opentype.js";
import { useEffect, useId, useState } from "react";
import { cn } from "@/lib/utils";

const DEFAULT_FONT_URL = "/fonts/IndieFlower-Regular.ttf";
const fontCache = new Map<string, Promise<opentype.Font>>();

function loadFont(url: string): Promise<opentype.Font> {
  const cached = fontCache.get(url);
  if (cached) return cached;

  const pending = fetch(url)
    .then((response) => {
      if (!response.ok) throw new Error(`Font request failed (${response.status})`);
      return response.arrayBuffer();
    })
    .then((buffer) => opentype.parse(buffer));

  fontCache.set(url, pending);
  return pending;
}

interface HandwritingSvgProps {
  path?: string;
  text?: string;
  fontUrl?: string;
  className?: string;
  strokeClassName?: string;
  duration?: number;
  delay?: number;
  strokeWidth?: number;
  width?: number;
  height?: number;
  fontSize?: number;
  ease?: "linear" | "easeIn" | "easeOut" | "easeInOut";
  label?: string;
}

export function HandwritingSvg({
  path: pathProp,
  text,
  fontUrl = DEFAULT_FONT_URL,
  className,
  strokeClassName,
  duration = 2.2,
  delay = 0.35,
  strokeWidth = 1.35,
  width = 320,
  height = 88,
  fontSize = 58,
  ease = "easeInOut",
  label,
}: HandwritingSvgProps) {
  const [generatedPath, setGeneratedPath] = useState<string | null>(null);
  const [viewBox, setViewBox] = useState(`0 0 ${width} ${height}`);
  const [failed, setFailed] = useState(false);
  const reduceMotion = useReducedMotion();
  const titleId = useId();

  useEffect(() => {
    if (!text || pathProp) return;

    let cancelled = false;

    loadFont(fontUrl)
      .then((font) => {
        if (cancelled) return;
        setFailed(false);
        const generated = font.getPath(text, 0, fontSize, fontSize);
        const box = generated.getBoundingBox();
        const pad = Math.max(4, strokeWidth * 3);
        setViewBox(
          `${Math.floor(box.x1 - pad)} ${Math.floor(box.y1 - pad)} ${Math.ceil(box.x2 - box.x1 + pad * 2)} ${Math.ceil(box.y2 - box.y1 + pad * 2)}`,
        );
        setGeneratedPath(generated.toPathData(2));
      })
      .catch(() => {
        if (!cancelled) {
          fontCache.delete(fontUrl);
          setGeneratedPath(null);
          setFailed(true);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [fontSize, fontUrl, height, pathProp, strokeWidth, text, width]);

  const resolvedPath = pathProp ?? generatedPath;

  if (!resolvedPath) {
    return (
      <span
        className={cn("inline-flex items-center font-hand text-[0.86em] text-current", className)}
        style={{ width, minHeight: height }}
        aria-label={label ?? text}
      >
        {failed ? text : null}
      </span>
    );
  }

  const accessibleLabel = label ?? text ?? "Handwritten annotation";

  return (
    <svg
      width={width}
      height={height}
      viewBox={pathProp ? `0 0 ${width} ${height}` : viewBox}
      preserveAspectRatio="xMinYMid meet"
      className={cn("block overflow-visible text-current", className)}
      role="img"
      aria-labelledby={titleId}
    >
      <title id={titleId}>{accessibleLabel}</title>
      <motion.path
        d={resolvedPath}
        fill="currentColor"
        fillOpacity={1}
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
        className={strokeClassName}
        initial={reduceMotion ? false : { pathLength: 0, opacity: 0.35, fillOpacity: 0 }}
        animate={{ pathLength: 1, opacity: 1, fillOpacity: 1 }}
        transition={
          reduceMotion
            ? { duration: 0 }
            : {
                pathLength: { delay, duration, ease },
                opacity: { delay, duration: Math.min(0.5, duration / 3) },
                fillOpacity: { delay: delay + duration * 0.72, duration: 0.45, ease: "easeOut" },
              }
        }
      />
    </svg>
  );
}

export default HandwritingSvg;
