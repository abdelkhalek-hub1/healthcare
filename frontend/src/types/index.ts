export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface ChatMessage {
  id?: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  correlation_id?: string;
  intent?: string;
  agent?: string;
  token_usage?: TokenUsage | null;
  /** Structured payload returned by specialized agents (e.g. consultation, reimbursement). */
  data?: Record<string, any> | null;
  metadata?: Record<string, any>;
}

export interface Session {
  id: string;
  user_id?: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_intent?: string | null;
  metadata?: Record<string, any>;
}

export interface ServiceHealth {
  name: string;
  status: "healthy" | "degraded" | "unhealthy";
  latency_ms?: number | null;
  error?: string | null;
  checked_at: string;
}

export interface SystemHealth {
  status: "healthy" | "degraded" | "unhealthy";
  version: string;
  uptime_seconds: number;
  timestamp: string;
  services: Record<string, ServiceHealth>;
  metrics: Record<string, any>;
}

export interface MonitoringLog {
  correlation_id: string;
  session_id: string;
  timestamp: string;
  selected_agent: string;
  intent: string;
  latency_ms: number;
  execution_time_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  status: "success" | "error";
  error?: string | null;
}

export interface SystemMetrics {
  total_requests: number;
  success_count: number;
  error_count: number;
  avg_latency_ms: number;
  total_tokens: number;
  success_rate: number;
  satisfaction_rate: number;
}

export interface AgentMetric {
  agent: string;
  count: number;
  avg_latency_ms: number;
}
