import type { Metadata } from "next";
import { Space_Grotesk, Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

// Display: technical, credible for an agent/ops tool. Used with restraint.
const display = Space_Grotesk({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

// Body: legible workhorse for data-dense UI.
const sans = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

// Data face: citation ids, similarity scores, intents, planned-action JSON.
// Mono here *means* "system data", not decoration.
const mono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Sentinel — support triage that shows its work",
  description:
    "Sentinel routes each support request, answers only with citations it can prove, and escalates the rest to a human.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`dark ${display.variable} ${sans.variable} ${mono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
