"use client";

import * as React from "react";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

// ── Public types ──────────────────────────────────────────────────────────────
export interface CTAConfig {
  label: string;
  href?: string;
  onClick?: () => void;
}

export interface InteractiveStarfieldHeroProps {
  /** Number of particles. @default 300 */
  particleCount?: number;
  /** Cursor influence radius in px. @default 140 */
  interactionRadius?: number;
  /** Base particle colour (hex). @default "#60a5fa" */
  particleColor?: string;
  /** Particle colour at full activation (hex). @default "#ffffff" */
  activeColor?: string;
  /** Return speed: 0.1 (dreamlike) → 1.0 (snappy). @default 0.5 */
  speed?: number;
  className?: string;
  /** Override default hero content. */
  children?: React.ReactNode;
  title?: string;
  subtitle?: string;
  primaryCTA?: CTAConfig;
  secondaryCTA?: CTAConfig;
}

// ── Internal particle ─────────────────────────────────────────────────────────
type Star = {
  ox: number;
  oy: number; // resting origin
  x: number;
  y: number; // physics position (starts = origin)
  vx: number;
  vy: number;
  r: number; // base radius (0.8 – 2.2 px)
  alpha: number; // base opacity (0.15 – 0.7)
  phase: number; // twinkle phase
  rot: number; // fixed rest rotation for very-dim stars
};

// ── Colour helpers ────────────────────────────────────────────────────────────
type RGB = [number, number, number];

function hexToRgb(hex: string): RGB {
  const ctx = document.createElement("canvas").getContext("2d")!;
  ctx.fillStyle = hex;
  const h = ctx.fillStyle.replace("#", "");
  return [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16),
  ];
}

function lerpRgb(a: RGB, b: RGB, t: number): string {
  return `rgb(${Math.round(a[0] + (b[0] - a[0]) * t)},${Math.round(a[1] + (b[1] - a[1]) * t)},${Math.round(a[2] + (b[2] - a[2]) * t)})`;
}

// ── Canvas starfield ──────────────────────────────────────────────────────────
interface CanvasProps {
  particleCount: number;
  interactionRadius: number;
  baseRgb: RGB;
  activeRgb: RGB;
  springK: number;
  damping: number;
  reduceMotion: boolean;
}

function StarfieldCanvas({
  particleCount,
  interactionRadius,
  baseRgb,
  activeRgb,
  springK,
  damping,
  reduceMotion,
}: CanvasProps) {
  const canvasRef = React.useRef<HTMLCanvasElement>(null);
  const mouseRef = React.useRef({ x: -9999, y: -9999, active: false });
  const starsRef = React.useRef<Star[]>([]);
  const rafRef = React.useRef<number>(0);
  // Global influence fades in on enter, out on leave
  const influenceRef = React.useRef(0);

  // ── Seed stars ────────────────────────────────────────────────────────────
  function seedStars(W: number, H: number): Star[] {
    return Array.from({ length: particleCount }, () => {
      const ox = Math.random() * W;
      const oy = Math.random() * H;
      return {
        ox,
        oy,
        x: ox,
        y: oy,
        vx: 0,
        vy: 0,
        r: 0.8 + Math.random() * 1.4,
        alpha: 0.12 + Math.random() * 0.55,
        phase: Math.random() * Math.PI * 2,
        rot: Math.random() * Math.PI * 2,
      };
    });
  }

  // ── Mouse / touch ─────────────────────────────────────────────────────────
  React.useEffect(() => {
    const update = (cx: number, cy: number) => {
      const cvs = canvasRef.current;
      if (!cvs) return;
      const r = cvs.getBoundingClientRect();
      mouseRef.current = { x: cx - r.left, y: cy - r.top, active: true };
    };
    const onMove = (e: MouseEvent) => update(e.clientX, e.clientY);
    const onTouch = (e: TouchEvent) => {
      if (e.touches[0]) update(e.touches[0].clientX, e.touches[0].clientY);
    };
    const onLeave = () => {
      mouseRef.current.active = false;
    };

    window.addEventListener("mousemove", onMove, { passive: true });
    window.addEventListener("touchmove", onTouch, { passive: true });
    window.addEventListener("mouseleave", onLeave);
    window.addEventListener("touchend", onLeave);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("touchmove", onTouch);
      window.removeEventListener("mouseleave", onLeave);
      window.removeEventListener("touchend", onLeave);
    };
  }, []);

  // ── Render loop ───────────────────────────────────────────────────────────
  React.useEffect(() => {
    const cvs = canvasRef.current;
    if (!cvs) return;
    const ctx = cvs.getContext("2d");
    if (!ctx) return;

    const c = ctx;
    const el = cvs;
    let W = 0,
      H = 0,
      dpr = 1;
    const MAX_STRETCH = 18;
    const REPULSE_STR = 1.8;

    function resize() {
      dpr = Math.min(window.devicePixelRatio ?? 1, 2);
      W = el.offsetWidth;
      H = el.offsetHeight;
      el.width = W * dpr;
      el.height = H * dpr;
      c.setTransform(dpr, 0, 0, dpr, 0, 0);
      starsRef.current = seedStars(W, H);
    }

    let t0 = performance.now();

    const isVisibleRef = { current: true };

    const io = new IntersectionObserver(
      ([e]) => {
        isVisibleRef.current = e?.isIntersecting ?? true;
        if (isVisibleRef.current && !document.hidden && !rafRef.current) {
          t0 = performance.now();
          rafRef.current = requestAnimationFrame(draw);
        }
      },
      { threshold: 0.01 },
    );
    io.observe(el);

    function onVisibilityChange() {
      if (!document.hidden && isVisibleRef.current && !rafRef.current) {
        t0 = performance.now();
        rafRef.current = requestAnimationFrame(draw);
      }
    }
    document.addEventListener("visibilitychange", onVisibilityChange);

    function draw(now: number) {
      if (document.hidden || !isVisibleRef.current) {
        rafRef.current = 0;
        return;
      }
      const elapsed = (now - t0) / 1000;
      c.clearRect(0, 0, W, H);

      const mx = mouseRef.current.x;
      const my = mouseRef.current.y;
      const active = mouseRef.current.active && !reduceMotion;

      // Fade global influence in/out smoothly
      if (active) {
        influenceRef.current = Math.min(1, influenceRef.current + 0.06);
      } else {
        influenceRef.current = Math.max(0, influenceRef.current - 0.03);
      }
      const inf = influenceRef.current;
      const ir2 = interactionRadius * interactionRadius;

      for (const s of starsRef.current) {
        // ── Physics ──────────────────────────────────────────────────────
        const dx = s.x - mx;
        const dy = s.y - my;
        const dist2 = dx * dx + dy * dy;
        const dist = Math.sqrt(dist2);

        let t = 0; // activation 0-1
        if (inf > 0.01 && dist2 < ir2) {
          t = (1 - dist / interactionRadius) ** 2 * inf;
        }

        if (t > 0.01 && dist > 0.1) {
          s.vx += (dx / dist) * REPULSE_STR * t;
          s.vy += (dy / dist) * REPULSE_STR * t;
        }
        s.vx += (s.ox - s.x) * springK;
        s.vy += (s.oy - s.y) * springK;
        s.vx *= damping;
        s.vy *= damping;
        s.x += s.vx;
        s.y += s.vy;

        // ── Visual ───────────────────────────────────────────────────────
        const twinkle = reduceMotion
          ? 0
          : Math.sin(elapsed * 1.4 + s.phase) * 0.5 + 0.5;
        const baseA = s.alpha * (0.55 + twinkle * 0.45);
        const drawAlpha = Math.min(1, baseA + t * (1 - baseA));

        // Stretch away from cursor
        const stretchH = s.r * 2 + t * MAX_STRETCH;
        const stretchW = s.r * 2; // constant width — keeps it as a dash

        // Rotation: at rest uses s.rot; active aligns to repulsion direction
        const velMag = Math.sqrt(s.vx * s.vx + s.vy * s.vy);
        const drawRot =
          velMag > 0.3
            ? Math.atan2(s.vy, s.vx) + Math.PI / 2 // align long axis with velocity
            : s.rot;

        const color =
          t > 0.01
            ? lerpRgb(baseRgb, activeRgb, t)
            : lerpRgb(baseRgb, activeRgb, 0);

        c.save();
        c.translate(s.x, s.y);
        c.rotate(drawRot);
        c.globalAlpha = drawAlpha;
        c.fillStyle = color;

        // Glow halo for bright active stars
        if (t > 0.4) {
          c.shadowBlur = 6 + t * 10;
          c.shadowColor = color;
        } else {
          c.shadowBlur = 0;
        }

        // Rounded-pill shape
        const hw = stretchW / 2;
        const hh = stretchH / 2;
        const cr = Math.min(hw, hh);
        c.beginPath();
        c.moveTo(-hw + cr, -hh);
        c.lineTo(hw - cr, -hh);
        c.quadraticCurveTo(hw, -hh, hw, -hh + cr);
        c.lineTo(hw, hh - cr);
        c.quadraticCurveTo(hw, hh, hw - cr, hh);
        c.lineTo(-hw + cr, hh);
        c.quadraticCurveTo(-hw, hh, -hw, hh - cr);
        c.lineTo(-hw, -hh + cr);
        c.quadraticCurveTo(-hw, -hh, -hw + cr, -hh);
        c.closePath();
        c.fill();
        c.restore();
      }

      c.globalAlpha = 1;
      c.shadowBlur = 0;
      rafRef.current = requestAnimationFrame(draw);
    }

    const ro = new ResizeObserver(resize);
    ro.observe(el);
    resize();
    t0 = performance.now();
    rafRef.current = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(rafRef.current);
      ro.disconnect();
      io.disconnect();
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [
    particleCount,
    interactionRadius,
    baseRgb,
    activeRgb,
    springK,
    damping,
    reduceMotion,
  ]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className="absolute inset-0 h-full w-full"
      style={{ pointerEvents: "none" }}
    />
  );
}

// ── Motion presets ────────────────────────────────────────────────────────────
const UP = {
  hidden: { opacity: 0, y: 22 },
  show: { opacity: 1, y: 0 },
};
const EASE = [0.22, 1, 0.36, 1] as const;

// ── Hero component ─────────────────────────────────────────────────────────────
export function InteractiveStarfieldHero({
  particleCount = 300,
  interactionRadius = 140,
  particleColor = "#818cf8",
  activeColor = "#e9e9ff",
  speed = 0.5,
  className,
  children,
  title = "Ship faster.\nBuild better.",
  subtitle = "A motion-native component library for React — animated, accessible, and production-ready.",
  primaryCTA = { label: "Get started", href: "#" },
  secondaryCTA = { label: "View components", href: "#" },
}: InteractiveStarfieldHeroProps) {
  const reduceMotion = useReducedMotion() === true;

  // Parse colours once on mount / when props change
  const [baseRgb, setBaseRgb] = React.useState<[number, number, number]>([
    96, 165, 250,
  ]);
  const [activeRgb, setActiveRgb] = React.useState<[number, number, number]>([
    255, 255, 255,
  ]);

  React.useEffect(() => {
    setBaseRgb(hexToRgb(particleColor));
    setActiveRgb(hexToRgb(activeColor));
  }, [particleColor, activeColor]);

  // Derive spring / damping from speed prop
  const springK = 0.022 + speed * 0.068;
  const damping = 0.9 - speed * 0.13;

  const titleLines = (title ?? "").split("\n");

  return (
    <section
      className={cn(
        "relative isolate flex min-h-[calc(100svh-4rem)] items-center overflow-hidden rounded-3xl",
        "bg-zinc-950",
        className,
      )}
    >
      {/* ── Particle canvas ── */}
      <StarfieldCanvas
        particleCount={particleCount}
        interactionRadius={interactionRadius}
        baseRgb={baseRgb}
        activeRgb={activeRgb}
        springK={springK}
        damping={damping}
        reduceMotion={reduceMotion}
      />

      {/* ── Radial edge vignette ── */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 rounded-3xl"
        style={{
          background:
            "radial-gradient(ellipse 90% 80% at 50% 50%, transparent 40%, rgba(9,9,11,0.92) 100%)",
        }}
      />

      {/* ── Content ── */}
      <div className="relative z-10 w-full px-8 py-20 sm:px-14 lg:px-20">
        {children ? (
          children
        ) : (
          <motion.div
            className="max-w-2xl"
            initial="hidden"
            animate="show"
            variants={{ show: { transition: { staggerChildren: 0.11 } } }}
          >
            {/* Eyebrow */}
            <motion.div
              variants={UP}
              transition={{ duration: 0.55, ease: EASE }}
              className="mb-7 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.06] px-4 py-1.5 backdrop-blur-sm"
            >
              <span className="size-1.5 animate-pulse rounded-full bg-blue-400" />
              <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-white/55">
                Interactive component
              </span>
            </motion.div>

            {/* Title */}
            <motion.h1
              variants={UP}
              transition={{ duration: 0.7, ease: EASE }}
              className="text-balance text-5xl font-bold tracking-[-0.025em] text-white sm:text-6xl lg:text-7xl"
            >
              {titleLines.map((line, i) => (
                <React.Fragment key={i}>
                  {i === 0 ? (
                    line
                  ) : (
                    <span className="text-white/45">{line}</span>
                  )}
                  {i < titleLines.length - 1 && <br />}
                </React.Fragment>
              ))}
            </motion.h1>

            {/* Subtitle */}
            {subtitle && (
              <motion.p
                variants={UP}
                transition={{ duration: 0.6, ease: EASE }}
                className="mt-6 max-w-lg text-[15px] leading-relaxed text-white/40"
              >
                {subtitle}
              </motion.p>
            )}

            {/* CTAs */}
            <motion.div
              variants={UP}
              transition={{ duration: 0.55, ease: EASE }}
              className="mt-10 flex flex-wrap gap-3"
            >
              {primaryCTA && (
                <a
                  href={primaryCTA.href ?? "#"}
                  onClick={primaryCTA.onClick}
                  className="group inline-flex items-center gap-2 rounded-full bg-white px-6 py-2.5 text-sm font-semibold text-zinc-900 shadow-[0_0_20px_rgba(255,255,255,.12)] transition-all duration-200 hover:gap-3 hover:bg-white/90 hover:shadow-[0_0_28px_rgba(255,255,255,.22)]"
                >
                  {primaryCTA.label}
                  <ArrowRight className="size-3.5 transition-transform duration-200 group-hover:translate-x-0.5" />
                </a>
              )}
              {secondaryCTA && (
                <a
                  href={secondaryCTA.href ?? "#"}
                  onClick={secondaryCTA.onClick}
                  className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.05] px-6 py-2.5 text-sm font-medium text-white/65 backdrop-blur-sm transition-all duration-200 hover:border-white/20 hover:bg-white/[0.09] hover:text-white"
                >
                  {secondaryCTA.label}
                </a>
              )}
            </motion.div>
          </motion.div>
        )}
      </div>
    </section>
  );
}

export default InteractiveStarfieldHero;
