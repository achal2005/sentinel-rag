export type RouteKey = "answer" | "action" | "escalate" | "spam";
export type Urgency = "low" | "medium" | "high";
export type Channel = "email" | "whatsapp" | "web_form";
export type InboxStatus = "answered" | "action_needed" | "escalated" | "spam";

export interface Source {
  citation_id: string | null;
  doc: string;
  heading: string;
  similarity: number;
}

export interface PlannedAction {
  intent: string;
  urgency: string;
  status: string;
  request: string;
}

export interface TriageResult {
  query: string;
  route: RouteKey;
  intent: string;
  urgency: Urgency;
  action_required: boolean;
  answer: string;
  escalated: boolean;
  reason: string;
  citations: string[];
  sources: Source[];
  action: PlannedAction | null;
  latency_ms: number;
  run_id: number | null;
  llm_calls: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
  confidence_min: number;
}

// One row in the session transcript.
export interface TriageRecord extends TriageResult {
  id: string;
  at: number; // epoch ms
}

// --- approval queue (Week 3 safety) ---------------------------------------

export type RiskLevel = "low" | "medium" | "high";
export type ApprovalStatus = "pending" | "approved" | "rejected" | "executed";

// A high-risk action parked in the approval_queue, awaiting a human decision.
export interface ApprovalItem {
  id: number;
  created_at: string; // ISO timestamp
  tool: string;
  risk_level: RiskLevel;
  status: ApprovalStatus;
  reason: string | null;
  request: string | null;
  urgency: string | null;
  run_id: number | null;
  params: Record<string, unknown>;
}

// Result of approving/rejecting an item.
export interface ApprovalActionResult {
  id: number;
  tool: string | null;
  status: ApprovalStatus;
  executed: boolean;
  error: string | null;
}

// --- evals (real report) ---------------------------------------------------

export interface EvalCapability {
  key: string;
  label: string;
  passed: number;
  denominator: number;
  rate: number; // 0..1
}

export interface EvalSummary {
  generatedAt: string | null;
  total: number;
  passed: number;
  failed: number;
  passRate: number; // 0..1
  criticalPassed: boolean | null;
  dataset: string | null;
  version: string | null;
  totalCases: number | null;
  semanticJudge: string | null;
  tools: string[];
  capabilities: EvalCapability[];
}

// --- runs (real triage history) -------------------------------------------

// One row of the Inbox — a real graph run from the `runs` table.
export interface RunRow {
  id: number;
  created_at: string;
  channel: Channel;
  sender: string | null;
  request: string;
  route: RouteKey;
  reason: string | null;
  escalated: boolean;
  model: string | null;
  total_tokens: number;
  cost_usd: number;
  latency_ms: number;
  action_status: string | null;
}

export interface RunAuditStep {
  step: string; // router | retrieve | tool | outcome
  detail: Record<string, unknown>;
}

export interface RunDetail extends RunRow {
  citations: string[];
  sources: Source[];
  steps: RunAuditStep[];
}

// --- aggregate usage stats -------------------------------------------------

export interface StatBreakdown {
  label: string;
  count: number;
}

export interface UsageStats {
  requests_today: number;
  pending_approvals: number;
  avg_latency_ms: number;
  escalation_rate: number; // 0..1
  cost_today: number;
  cost_mtd: number;
  model_split: StatBreakdown[];
  channel_split: StatBreakdown[];
}

// --- public runtime configuration -----------------------------------------

export interface RegisteredTool {
  name: string;
  risk_level: RiskLevel;
  required_params: string[];
}

export interface SystemInfo {
  service: string;
  version: string;
  provider: string;
  embed_provider: string;
  chat_model: string;
  embed_model: string;
  retrieval_topk: number;
  confidence_min: number;
  tools: RegisteredTool[];
  tracing_enabled: boolean;
  langfuse_enabled: boolean;
}

// UI-only shape for live values rendered in a compact stat card.
export interface UsageStat {
  label: string;
  value: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  hint: string;
  trend?: number;
  tone?: "neutral" | "answer" | "action" | "escalate" | "brand";
}
