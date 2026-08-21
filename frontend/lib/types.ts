export type RouteKey = "answer" | "action" | "escalate" | "spam";
export type Urgency = "low" | "medium" | "high";

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
