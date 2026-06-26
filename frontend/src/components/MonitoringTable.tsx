import React, { useState } from "react";
import { Loader2 } from "lucide-react";
import { MonitoringLog } from "../types";
import { StatusBadge } from "./StatusBadge";
import { CheckCircle2, XCircle, ChevronDown, ChevronUp, Copy, Check } from "lucide-react";

interface MonitoringTableProps {
  logs: MonitoringLog[];
  loading?: boolean;
}

export const MonitoringTable: React.FC<MonitoringTableProps> = ({ logs, loading = false }) => {
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const toggleRow = (id: string) => {
    setExpandedRow(expandedRow === id ? null : id);
  };

  const handleCopy = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  if (loading && logs.length === 0) {
    return (
      <div className="bg-white dark:bg-dark-card border border-slate-200 dark:border-dark-border p-12 text-center rounded-2xl flex flex-col items-center gap-3">
        <Loader2 className="w-7 h-7 text-brand-500 animate-spin" />
        <span className="text-slate-400 dark:text-slate-500 text-sm font-semibold">Loading telemetry data…</span>
      </div>
    );
  }

  if (logs.length === 0) {
    return (
      <div className="bg-white dark:bg-dark-card border border-slate-200 dark:border-dark-border p-12 text-center rounded-2xl">
        <span className="text-slate-400 dark:text-slate-500 text-sm font-semibold">
          No telemetry logs available. Run some chats to generate records.
        </span>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-dark-card border border-slate-200 dark:border-dark-border rounded-2xl overflow-hidden shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 dark:bg-dark-input border-b border-slate-200 dark:border-dark-border text-slate-400 dark:text-slate-500 text-[10px] font-bold uppercase tracking-wider">
              <th className="py-4 px-6">Status</th>
              <th className="py-4 px-6">Correlation ID</th>
              <th className="py-4 px-6">Intent</th>
              <th className="py-4 px-6">Agent Node</th>
              <th className="py-4 px-6">Latency</th>
              <th className="py-4 px-6">Tokens</th>
              <th className="py-4 px-6 text-right">Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-dark-border/40 text-xs">
            {logs.map((log) => {
              const isExpanded = expandedRow === log.correlation_id;
              const hasError = log.status === "error" || !!log.error;
              return (
                <React.Fragment key={log.correlation_id}>
                  <tr
                    onClick={() => toggleRow(log.correlation_id)}
                    className="hover:bg-slate-50/50 dark:hover:bg-brand-950/5 cursor-pointer transition-colors duration-100"
                  >
                    {/* Status Column */}
                    <td className="py-4 px-6">
                      {hasError ? (
                        <XCircle className="w-5 h-5 text-rose-500" />
                      ) : (
                        <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                      )}
                    </td>

                    {/* Correlation ID Column */}
                    <td className="py-4 px-6 font-mono text-slate-500 dark:text-slate-400">
                      <div className="flex items-center gap-2">
                        <span>{log.correlation_id.slice(0, 13)}...</span>
                        <button
                          onClick={(e) => handleCopy(log.correlation_id, e)}
                          className="text-slate-400 hover:text-slate-600 dark:hover:text-dark-text p-0.5 rounded transition-colors"
                          title="Copy ID"
                        >
                          {copiedId === log.correlation_id ? (
                            <Check className="w-3.5 h-3.5 text-emerald-500" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    </td>

                    {/* Intent Column */}
                    <td className="py-4 px-6">
                      <StatusBadge agent={log.intent} />
                    </td>

                    {/* Agent Column */}
                    <td className="py-4 px-6 font-semibold text-slate-700 dark:text-dark-text">
                      {log.selected_agent}
                    </td>

                    {/* Latency Column */}
                    <td className="py-4 px-6 text-slate-600 dark:text-slate-300 font-medium">
                      {log.latency_ms.toFixed(0)} ms
                    </td>

                    {/* Tokens Column */}
                    <td className="py-4 px-6 text-slate-500 dark:text-slate-400 font-semibold">
                      {log.total_tokens > 0 ? log.total_tokens : "-"}
                    </td>

                    {/* Time Column */}
                    <td className="py-4 px-6 text-right text-slate-400 dark:text-slate-500 font-medium">
                      <div className="flex items-center justify-end gap-1.5">
                        <span>
                          {new Date(log.timestamp).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                            second: "2-digit",
                          })}
                        </span>
                        {hasError ? (
                          isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />
                        ) : (
                          <div className="w-4 h-4"></div>
                        )}
                      </div>
                    </td>
                  </tr>

                  {/* Expanded Row for Error Details */}
                  {isExpanded && hasError && (
                    <tr className="bg-rose-50/20 dark:bg-rose-950/5">
                      <td colSpan={7} className="py-3.5 px-8 border-l-4 border-rose-500 text-xs">
                        <div className="space-y-1">
                          <span className="font-bold text-rose-800 dark:text-rose-400">Execution Error Trace:</span>
                          <pre className="font-mono text-rose-700 dark:text-rose-300/80 bg-rose-500/5 p-3 rounded-lg overflow-x-auto whitespace-pre-wrap max-w-full">
                            {log.error || "Unknown graph execution failure."}
                          </pre>
                          <div className="text-[10px] text-slate-400 dark:text-slate-500 pt-1">
                            Session Context ID: <span className="font-mono">{log.session_id}</span>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
