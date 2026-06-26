import React, { useEffect, useState } from "react";
import { RefreshCw, AlertCircle, CheckCircle, XCircle, Activity, Server, Database, Brain } from "lucide-react";
import { healthService } from "../services/api";
import { SystemHealth, ServiceHealth } from "../types";
import { StatusBadge } from "../components/StatusBadge";

const serviceIcons: Record<string, React.ReactNode> = {
  mongodb: <Database className="w-5 h-5" />,
  groq: <Brain className="w-5 h-5" />,
  langgraph: <Activity className="w-5 h-5" />,
};

const statusColors = {
  healthy: {
    bg: "bg-emerald-50 dark:bg-emerald-950/20",
    border: "border-emerald-200 dark:border-emerald-800/40",
    icon: "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600",
    dot: "bg-emerald-500",
  },
  degraded: {
    bg: "bg-amber-50 dark:bg-amber-950/20",
    border: "border-amber-200 dark:border-amber-800/40",
    icon: "bg-amber-100 dark:bg-amber-900/40 text-amber-600",
    dot: "bg-amber-500",
  },
  unhealthy: {
    bg: "bg-rose-50 dark:bg-rose-950/20",
    border: "border-rose-200 dark:border-rose-800/40",
    icon: "bg-rose-100 dark:bg-rose-900/40 text-rose-600",
    dot: "bg-rose-500",
  },
};

const ServiceCard: React.FC<{ name: string; health: ServiceHealth }> = ({
  name,
  health,
}) => {
  const colors = statusColors[health.status] ?? statusColors.unhealthy;
  const Icon = serviceIcons[name.toLowerCase()] ?? <Server className="w-5 h-5" />;

  return (
    <div
      className={`rounded-2xl border p-5 transition-all duration-200 ${colors.bg} ${colors.border}`}
    >
      <div className="flex items-start gap-4">
        <div className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 ${colors.icon}`}>
          {Icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <h3 className="font-bold text-slate-800 dark:text-dark-text text-sm capitalize">
              {name}
            </h3>
            <StatusBadge agent={health.status} />
          </div>
          <div className="mt-2 space-y-1.5">
            {health.latency_ms != null && (
              <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
                <Activity className="w-3.5 h-3.5" />
                <span>{Math.round(health.latency_ms)}ms round-trip</span>
              </div>
            )}
            {health.error && (
              <div className="flex items-start gap-1.5 text-xs text-rose-600 dark:text-rose-400">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                <span className="break-words">{health.error}</span>
              </div>
            )}
            <div className="text-[10px] text-slate-400 dark:text-slate-500">
              Checked {new Date(health.checked_at).toLocaleTimeString()}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export const HealthPage: React.FC = () => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await healthService.getHealth();
      setHealth(data);
    } catch (err: any) {
      setError(
        err.response?.data?.message ?? "Unable to reach the backend health endpoint."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const id = setInterval(fetchHealth, 15_000);
    return () => clearInterval(id);
  }, []);

  const overallColors = health
    ? statusColors[health.status] ?? statusColors.unhealthy
    : statusColors.healthy;

  return (
    <div className="p-8 space-y-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-dark-text tracking-tight">
            System Health
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Service connectivity checks · Auto-refreshes every 15s
          </p>
        </div>
        <button
          onClick={fetchHealth}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-200 dark:border-dark-border text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-dark-border text-sm font-medium transition-all duration-200 disabled:opacity-50 active:scale-95"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Check Now
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-800/40 text-rose-700 dark:text-rose-400 text-sm">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          {error}
        </div>
      )}

      {health && (
        <>
          {/* Overall Status Banner */}
          <div
            className={`rounded-2xl border p-6 flex items-center gap-5 ${overallColors.bg} ${overallColors.border}`}
          >
            <div className={`w-14 h-14 rounded-2xl flex items-center justify-center ${overallColors.icon} shadow-sm`}>
              {health.status === "healthy" ? (
                <CheckCircle className="w-7 h-7" />
              ) : health.status === "degraded" ? (
                <AlertCircle className="w-7 h-7" />
              ) : (
                <XCircle className="w-7 h-7" />
              )}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-1">
                <span className="text-lg font-bold text-slate-800 dark:text-dark-text">
                  System is{" "}
                  <span className="capitalize">{health.status}</span>
                </span>
                <span className={`w-2.5 h-2.5 rounded-full animate-ping ${overallColors.dot}`} />
              </div>
              <div className="flex flex-wrap gap-4 text-xs text-slate-500 dark:text-slate-400">
                <span>
                  Version <strong className="text-slate-700 dark:text-slate-300">v{health.version}</strong>
                </span>
                <span>
                  Uptime{" "}
                  <strong className="text-slate-700 dark:text-slate-300">
                    {Math.floor(health.uptime_seconds / 3600)}h{" "}
                    {Math.floor((health.uptime_seconds % 3600) / 60)}m
                  </strong>
                </span>
                <span>
                  Checked at{" "}
                  <strong className="text-slate-700 dark:text-slate-300">
                    {new Date(health.timestamp).toLocaleTimeString()}
                  </strong>
                </span>
              </div>
            </div>
          </div>

          {/* Services Grid */}
          <div>
            <h3 className="font-bold text-slate-700 dark:text-slate-200 text-sm mb-4">
              Service Dependencies
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(health.services).map(([name, svc]) => (
                <ServiceCard key={name} name={name} health={svc} />
              ))}
            </div>
          </div>

          {/* System Metrics */}
          {Object.keys(health.metrics).length > 0 && (
            <div>
              <h3 className="font-bold text-slate-700 dark:text-slate-200 text-sm mb-4">
                Raw Metrics
              </h3>
              <div className="bg-white dark:bg-dark-card rounded-2xl border border-slate-200 dark:border-dark-border p-5">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {Object.entries(health.metrics).map(([key, val]) => (
                    <div key={key} className="space-y-0.5">
                      <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">
                        {key.replace(/_/g, " ")}
                      </span>
                      <span className="text-sm font-bold text-slate-700 dark:text-slate-200">
                        {typeof val === "number" ? val.toLocaleString() : String(val)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {!health && !error && !loading && (
        <div className="flex flex-col items-center justify-center py-16 text-slate-400 dark:text-slate-500 gap-3">
          <Activity className="w-10 h-10 opacity-30" />
          <p className="text-sm">Loading health status…</p>
        </div>
      )}
    </div>
  );
};
