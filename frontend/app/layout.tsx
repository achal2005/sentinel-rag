import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sentinel — support operations console",
  description:
    "Sentinel keeps watch over every incoming request: it triages, answers only with citations it can prove, and raises a beacon when a human needs to decide.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="dark h-full antialiased">
      <body className="min-h-full">{children}</body>
    </html>
  );
}
