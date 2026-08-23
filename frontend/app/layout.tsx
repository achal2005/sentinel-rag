import type { Metadata } from "next";
import { Instrument_Serif, Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

// Distinctive type system: an editorial serif for large statements, a clean
// grotesk for UI/body, and a mono for data + citation tokens.
const display = Instrument_Serif({
  weight: "400",
  style: ["normal", "italic"],
  subsets: ["latin"],
  variable: "--font-instrument",
  display: "swap",
});
const sans = Geist({
  subsets: ["latin"],
  variable: "--font-geist",
  display: "swap",
});
const mono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-geist-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Sentinel — support operations console",
  description:
    "Sentinel keeps watch over every incoming request: it triages, answers only with citations it can prove, and raises a beacon when a human needs to decide.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      data-scroll-behavior="smooth"
      className={`dark h-full antialiased ${display.variable} ${sans.variable} ${mono.variable}`}
    >
      <body className="min-h-full">{children}</body>
    </html>
  );
}
