import { AppShell } from "@/components/shell/app-shell";

// Every console view lives under the app shell (sidebar + beacon header).
// The marketing landing at "/" sits outside this group, so it has no chrome.
export default function AppGroupLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
