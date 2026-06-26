import axios from "axios";
import {
  ChatMessage,
  Session,
  SystemHealth,
  MonitoringLog,
  SystemMetrics,
  AgentMetric,
} from "../types";

// Configure Axios with proxy-friendly baseURL
const api = axios.create({
  baseURL: "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

export const chatService = {
  /**
   * Submit a new chat message to the assistant.
   */
  async sendMessage(message: string, sessionId?: string | null): Promise<any> {
    const response = await api.post("/chat", { message, session_id: sessionId });
    return response.data;
  },

  /**
   * Submit thumbs up/down rating feedback for a response turn.
   */
  async submitFeedback(correlationId: string, rating: number, comment?: string | null): Promise<void> {
    await api.post("/feedback", { correlation_id: correlationId, rating, comment });
  },
};

export const sessionService = {
  /**
   * Fetch recent conversation sessions.
   */
  async getSessions(limit = 20): Promise<Session[]> {
    const response = await api.get(`/sessions?limit=${limit}`);
    return response.data;
  },

  /**
   * Get metadata detail for a session.
   */
  async getSessionDetail(sessionId: string): Promise<Session> {
    const response = await api.get(`/sessions/${sessionId}`);
    return response.data;
  },

  /**
   * Retrieve message turns history list for a session.
   */
  async getSessionHistory(sessionId: string, limit = 50): Promise<ChatMessage[]> {
    const response = await api.get(`/sessions/${sessionId}/history?limit=${limit}`);
    return response.data;
  },
};

export const monitoringService = {
  /**
   * Retrieve recent execution telemetry logs.
   */
  async getLogs(limit = 50): Promise<MonitoringLog[]> {
    const response = await api.get(`/monitoring?limit=${limit}`);
    return response.data;
  },

  /**
   * Retrieve system dashboard aggregate metrics.
   */
  async getMetrics(): Promise<SystemMetrics> {
    const response = await api.get("/monitoring/metrics");
    return response.data;
  },

  /**
   * Retrieve group statistics per specialized agent.
   */
  async getAgentBreakdown(): Promise<AgentMetric[]> {
    const response = await api.get("/monitoring/agents");
    return response.data;
  },
};

export const healthService = {
  /**
   * Retrieve live connectivity check status.
   */
  async getHealth(): Promise<SystemHealth> {
    const response = await api.get("/health");
    return response.data;
  },
};

export default api;
