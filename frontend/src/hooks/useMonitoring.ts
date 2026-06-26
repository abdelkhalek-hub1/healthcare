import { useState, useEffect, useCallback } from "react";
import { MonitoringLog, SystemMetrics, AgentMetric } from "../types";
import { monitoringService } from "../services/api";

/**
 * Hook that fetches and exposes telemetry data from the monitoring service.
 * Auto-refreshes on a configurable interval.
 */
export const useMonitoring = (refreshIntervalMs = 30_000) => {
  const [logs, setLogs] = useState<MonitoringLog[]>([]);
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [agentBreakdown, setAgentBreakdown] = useState<AgentMetric[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [logsData, metricsData, agentsData] = await Promise.all([
        monitoringService.getLogs(100),
        monitoringService.getMetrics(),
        monitoringService.getAgentBreakdown(),
      ]);
      setLogs(logsData);
      setMetrics(metricsData);
      setAgentBreakdown(agentsData);
    } catch (err: any) {
      console.error("Failed to fetch monitoring data:", err);
      setError("Failed to load monitoring data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const id = setInterval(fetchAll, refreshIntervalMs);
    return () => clearInterval(id);
  }, [fetchAll, refreshIntervalMs]);

  return { logs, metrics, agentBreakdown, loading, error, refresh: fetchAll };
};
