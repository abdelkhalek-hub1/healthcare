import React from "react";
import { Activity, RefreshCw, AlertCircle, Download } from "lucide-react";
import { MonitoringTable } from "../components/MonitoringTable";
import { MetricCard } from "../components/MetricCard";
import { useMonitoring } from "../hooks/useMonitoring";

export const MonitoringPage: React.FC = () => {
  const { logs, metrics, agentBreakdown, loading, error, refresh } =
    useMonitoring(30_000);

  const handleExportCsv = () => {
    if (logs.length === 0) return;
    const headers = [
      "correlation_id",
      "session_id",
      "timestamp",
      "intent",
      "selected_agent",
      "status",
      "latency_ms",
      "total_tokens",
    ];
    const rows = logs.map((l) =>
      [
        l.correlation_id,
        l.session_id,
        l.timestamp,
        l.intent,
        l.selected_agent,
        l.status,
        l.latency_ms,
        l.total_tokens,
      ].join(",")
    );
    const csv = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `telemetry_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-dark-text tracking-tight">
            Telemetry & Monitoring
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Real-time LangGraph execution traces · Auto-refreshes every 30s
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleExportCsv}
            disabled={logs.length === 0}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-200 dark:border-dark-border text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-dark-border text-sm font-medium transition-all duration-200 disabled:opacity-40 active:scale-95"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
          <button
            onClick={refresh}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-200 dark:border-dark-border text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-dark-border text-sm font-medium transition-all duration-200 disabled:opacity-50 active:scale-95"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-800/40 text-rose-700 dark:text-rose-400 text-sm">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Summary Metrics */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-5">
        <MetricCard
          title="Total Requests"
          value={metrics?.total_requests ?? 0}
          icon={<Activity className="w-5 h-5" />}
          color="brand"
          subtitle="All executions"
        />
        <MetricCard
          title="Success Rate"
          value={`${((metrics?.success_rate ?? 0) * 100).toFixed(1)}%`}
          icon={<Activity className="w-5 h-5" />}
          color="emerald"
          subtitle={`${metrics?.error_count ?? 0} errors`}
        />
        <MetricCard
          title="Avg Latency"
          value={`${Math.round(metrics?.avg_latency_ms ?? 0)}ms`}
          icon={<Activity className="w-5 h-5" />}
          color="amber"
          subtitle="Mean response time"
        />
        <MetricCard
          title="Total Tokens"
          value={(metrics?.total_tokens ?? 0).toLocaleString()}
          icon={<Activity className="w-5 h-5" />}
          color="violet"
          subtitle="Cumulative usage"
        />
      </div>

      {/* Agent breakdown mini-table */}
      {agentBreakdown.length > 0 && (
        <div className="bg-white dark:bg-dark-card rounded-2xl border border-slate-200 dark:border-dark-border p-6">
          <h3 className="font-bold text-slate-800 dark:text-dark-text text-sm mb-4">
            Agent Breakdown
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider border-b border-slate-100 dark:border-dark-border/60">
                  <th className="pb-3 pr-4">Agent</th>
                  <th className="pb-3 pr-4">Requests</th>
                  <th className="pb-3">Avg Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50 dark:divide-dark-border/30">
                {agentBreakdown.map((a) => (
                  <tr key={a.agent} className="group">
                    <td className="py-3 pr-4">
                      <span className="font-medium text-slate-700 dark:text-slate-200 capitalize">
                        {a.agent.replace(/_agent$/, "").replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-slate-500 dark:text-slate-400">
                      {a.count}
                    </td>
                    <td className="py-3 font-semibold text-slate-700 dark:text-slate-300">
                      {Math.round(a.avg_latency_ms)}ms
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Full execution trace log table */}
      <div>
        <h3 className="font-bold text-slate-800 dark:text-dark-text text-sm mb-4">
          Execution Trace Log
        </h3>
        <MonitoringTable logs={logs} loading={loading} />
      </div>
    </div>
  );
};
