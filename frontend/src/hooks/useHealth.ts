import { useState, useEffect, useCallback } from "react";
import { SystemHealth } from "../types";
import { healthService } from "../services/api";

export const useHealth = (pollIntervalMs = 15000) => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = useCallback(async () => {
    try {
      const data = await healthService.getHealth();
      setHealth(data);
      setError(null);
    } catch (err: any) {
      console.error("Health check failure:", err);
      setError("Failed to fetch health status.");
      // Mark overall status as unhealthy in case of network/connection error
      setHealth((prev) => {
        if (prev) {
          return {
            ...prev,
            status: "unhealthy",
          };
        }
        return null;
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();

    const interval = setInterval(() => {
      fetchHealth();
    }, pollIntervalMs);

    return () => clearInterval(interval);
  }, [fetchHealth, pollIntervalMs]);

  return {
    health,
    loading,
    error,
    refreshHealth: fetchHealth,
  };
};
