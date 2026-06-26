import React, { useEffect, useState } from "react";
import {
  Activity,
  MessageSquare,
  CheckCircle,
  XCircle,
  Zap,
  Clock,
  TrendingUp,
  Brain,
  Stethoscope,
  FileText,
  HelpCircle,
  RefreshCw,
} from "lucide-react";
import { MetricCard } from "../components/MetricCard";
import { StatusBadge } from "../components/StatusBadge";
import { monitoringService, healthService } from "../services/api";
import { SystemMetrics, AgentMetric, SystemHealth } from "../types";

interface DashboardPageProps {
  onNavigate: (tab: string) => void;
}

const agentIcons: Record<string, React.ReactNode> = {
  consultation_agent: <Stethoscope className="w-4 h-4" />,
  reimbursement_agent: <FileText className="w-4 h-4" />,
  followup_agent: <Activity className="w-4 h-4" />,
  faq_agent: <HelpCircle className="w-4 h-4" />,
};

const agentColors: Record<string, string> = {
  consultation_agent: "from-blue-500 to-cyan-500",
  reimbursement_agent: "from-emerald-500 to-teal-500",
  followup_agent: "from-amber-500 to-orange-500",
  faq_agent: "from-violet-500 to-purple-500",
};

export const DashboardPage: React.FC<DashboardPageProps> = ({ onNavigate }) => {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [agents, setAgents] = useState<AgentMetric[]>([]);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState(new Date());

  const fetchData = async () => {
    setLoading(true);
    try {
      const [m, a, h] = await Promise.all([
        monitoringService.getMetrics(),
        monitoringService.getAgentBreakdown(),
        healthService.getHealth(),
      ]);
      setMetrics(m);
      setAgents(a);
      setHealth(h);
      setLastRefreshed(new Date());
    } catch (err) {
      console.error("Dashboard load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, 30_000);
    return () => clearInterval(id);
  }, []);

  const totalAgentRequests = agents.reduce((sum, a) => sum + a.count, 0);

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-dark-text tracking-tight">
            System Dashboard
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Real-time overview of your Healthcare AI Router
          </p>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-200 dark:border-dark-border text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-dark-border text-sm font-medium transition-all duration-200 disabled:opacity-50 active:scale-95"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* System Health Banner */}
      {health && (
        <div
          className={`rounded-2xl p-5 border flex items-center gap-4 ${
            health.status === "healthy"
              ? "bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800/30"
              : health.status === "degraded"
              ? "bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800/30"
              : "bg-rose-50 dark:bg-rose-950/20 border-rose-200 dark:border-rose-800/30"
          }`}
        >
          <div
            className={`w-12 h-12 rounded-xl flex items-center justify-center ${
              health.status === "healthy"
                ? "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600"
                : health.status === "degraded"
                ? "bg-amber-100 dark:bg-amber-900/40 text-amber-600"
                : "bg-rose-100 dark:bg-rose-900/40 text-rose-600"
            }`}
          >
            <Brain className="w-6 h-6" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-800 dark:text-dark-text text-sm">
                System Status
              </span>
              <StatusBadge agent={health.status} />
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              v{health.version} · Uptime{" "}
              {Math.floor(health.uptime_seconds / 3600)}h{" "}
              {Math.floor((health.uptime_seconds % 3600) / 60)}m · Last
              checked {new Date(health.timestamp).toLocaleTimeString()}
            </p>
          </div>
          <button
            onClick={() => onNavigate("health")}
            className="text-xs font-semibold text-brand-600 dark:text-brand-400 hover:underline"
          >
            View Details →
          </button>
        </div>
      )}

      {/* Key Metrics */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-5">
        <MetricCard
          title="Total Requests"
          value={metrics?.total_requests ?? 0}
          icon={<MessageSquare className="w-5 h-5" />}
          color="brand"
          subtitle="All-time queries"
        />
        <MetricCard
          title="Success Rate"
          value={`${((metrics?.success_rate ?? 0) * 100).toFixed(1)}%`}
          icon={<CheckCircle className="w-5 h-5" />}
          color="emerald"
          subtitle={`${metrics?.success_count ?? 0} succeeded`}
        />
        <MetricCard
          title="Avg Latency"
          value={`${Math.round(metrics?.avg_latency_ms ?? 0)}ms`}
          icon={<Clock className="w-5 h-5" />}
          color="amber"
          subtitle="Per response"
        />
        <MetricCard
          title="Total Tokens"
          value={(metrics?.total_tokens ?? 0).toLocaleString()}
          icon={<Zap className="w-5 h-5" />}
          color="violet"
          subtitle="LLM consumption"
        />
      </div>

      {/* Second row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Agent Breakdown */}
        <div className="lg:col-span-2 bg-white dark:bg-dark-card rounded-2xl border border-slate-200 dark:border-dark-border p-6">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h3 className="font-bold text-slate-800 dark:text-dark-text text-base">
                Agent Performance
              </h3>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
                Requests handled per specialized agent
              </p>
            </div>
            <TrendingUp className="w-5 h-5 text-slate-400" />
          </div>

          {agents.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 text-slate-400 dark:text-slate-500 gap-2">
              <Activity className="w-8 h-8 opacity-40" />
              <span className="text-sm">No agent data yet</span>
            </div>
          ) : (
            <div className="space-y-4">
              {agents.map((agent) => {
                const pct =
                  totalAgentRequests > 0
                    ? (agent.count / totalAgentRequests) * 100
                    : 0;
                const gradient =
                  agentColors[agent.agent] || "from-slate-400 to-slate-500";
                const label = agent.agent
                  .replace(/_agent$/, "")
                  .replace(/_/g, " ");
                return (
                  <div key={agent.agent} className="space-y-1.5">
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2 text-slate-700 dark:text-slate-200 font-medium capitalize">
                        <span
                          className={`w-7 h-7 rounded-lg bg-gradient-to-br ${gradient} flex items-center justify-center text-white`}
                        >
                          {agentIcons[agent.agent] ?? (
                            <Brain className="w-4 h-4" />
                          )}
                        </span>
                        {label}
                      </div>
                      <div className="flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
                        <span>{agent.count} req</span>
                        <span className="font-semibold text-slate-700 dark:text-slate-300">
                          {Math.round(agent.avg_latency_ms)}ms avg
                        </span>
                      </div>
                    </div>
                    <div className="h-2 bg-slate-100 dark:bg-dark-border rounded-full overflow-hidden">
                      <div
                        className={`h-full bg-gradient-to-r ${gradient} rounded-full transition-all duration-700`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="bg-white dark:bg-dark-card rounded-2xl border border-slate-200 dark:border-dark-border p-6 flex flex-col gap-4">
          <div>
            <h3 className="font-bold text-slate-800 dark:text-dark-text text-base">
              Quick Actions
            </h3>
            <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
              Navigate to key features
            </p>
          </div>
          <div className="space-y-2 flex-1">
            {[
              {
                id: "chat",
                label: "Start Consultation",
                sub: "New AI-assisted session",
                icon: <MessageSquare className="w-5 h-5" />,
                color: "text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-950/20",
              },
              {
                id: "monitoring",
                label: "View Telemetry",
                sub: "Execution trace logs",
                icon: <Activity className="w-5 h-5" />,
                color: "text-violet-600 dark:text-violet-400 bg-violet-50 dark:bg-violet-950/20",
              },
              {
                id: "history",
                label: "Session History",
                sub: "Past conversations",
                icon: <Clock className="w-5 h-5" />,
                color: "text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/20",
              },
              {
                id: "health",
                label: "System Health",
                sub: "Service connectivity",
                icon: <CheckCircle className="w-5 h-5" />,
                color: "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/20",
              },
            ].map((action) => (
              <button
                key={action.id}
                onClick={() => onNavigate(action.id)}
                className="w-full flex items-center gap-3 p-3.5 rounded-xl hover:bg-slate-50 dark:hover:bg-dark-border/50 transition-all duration-150 group text-left border border-transparent hover:border-slate-200 dark:hover:border-dark-border active:scale-[0.98]"
              >
                <div className={`p-2 rounded-lg ${action.color}`}>
                  {action.icon}
                </div>
                <div>
                  <div className="text-sm font-semibold text-slate-700 dark:text-slate-200 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">
                    {action.label}
                  </div>
                  <div className="text-xs text-slate-400 dark:text-slate-500">
                    {action.sub}
                  </div>
                </div>
              </button>
            ))}
          </div>
          <div className="pt-2 border-t border-slate-100 dark:border-dark-border/60">
            <p className="text-[10px] text-slate-400 dark:text-slate-500">
              Last refreshed: {lastRefreshed.toLocaleTimeString()}
            </p>
          </div>
        </div>
      </div>

      {/* Error metrics */}
      <div className="grid grid-cols-2 gap-5">
        <MetricCard
          title="Error Count"
          value={metrics?.error_count ?? 0}
          icon={<XCircle className="w-5 h-5" />}
          color="rose"
          subtitle="Failed requests"
        />
        <MetricCard
          title="Satisfaction Rate"
          value={`${((metrics?.satisfaction_rate ?? 0) * 100).toFixed(1)}%`}
          icon={<TrendingUp className="w-5 h-5" />}
          color="teal"
          subtitle="Based on user feedback"
        />
      </div>
    </div>
  );
};
