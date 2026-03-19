export type AgentCategory =
  | "data_flow"
  | "service_flow"
  | "architecture"
  | "code_quality"
  | "security"
  | "sdlc"
  | "performance";

export type Severity = "info" | "warning" | "critical";

export interface AgentInsight {
  agent_name: string;
  category: AgentCategory;
  title: string;
  description: string;
  severity: Severity;
  evidence: string[];
  recommendations: string[];
  confidence: number;
}

export interface DetectedPattern {
  pattern_type: string;
  description: string;
  entities_involved: string[];
  confidence: number;
  related_perspectives: string[];
}

export interface AgentRunResult {
  scan_id: string;
  run_id: string;
  status: "success" | "partial" | "failed";
  started_at: string;
  completed_at: string | null;
  insights: AgentInsight[];
  patterns: DetectedPattern[];
  agent_summaries: Record<string, string>;
  errors: string[];
}
