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
