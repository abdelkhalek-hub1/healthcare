import React from "react";
import {
  Calendar,
  HelpCircle,
  Receipt,
  Activity,
  AlertCircle,
  CheckCircle,
  AlertTriangle,
  XCircle,
} from "lucide-react";

interface StatusBadgeProps {
  agent: string;
}

type BadgeConfig = {
  label: string;
  bg: string;
  text: string;
  border: string;
  icon: React.ElementType;
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ agent }) => {
  const normalized = (agent ?? "").toLowerCase();

  const configs: Record<string, BadgeConfig> = {
    consultation: {
      label: "Consultation",
      bg: "bg-blue-500/10",
      text: "text-blue-600 dark:text-blue-400",
      border: "border-blue-500/20",
      icon: Calendar,
    },
    reimbursement: {
      label: "Reimbursement",
      bg: "bg-emerald-500/10",
      text: "text-emerald-600 dark:text-emerald-400",
      border: "border-emerald-500/20",
      icon: Receipt,
    },
    followup: {
      label: "Follow-up Care",
      bg: "bg-amber-500/10",
      text: "text-amber-600 dark:text-amber-400",
      border: "border-amber-500/20",
      icon: Activity,
    },
    faq: {
      label: "Medical FAQ",
      bg: "bg-purple-500/10",
      text: "text-purple-600 dark:text-purple-400",
      border: "border-purple-500/20",
      icon: HelpCircle,
    },
    error: {
      label: "Router Error",
      bg: "bg-rose-500/10",
      text: "text-rose-600 dark:text-rose-400",
      border: "border-rose-500/20",
      icon: AlertCircle,
    },
    healthy: {
      label: "Healthy",
      bg: "bg-emerald-500/10",
      text: "text-emerald-600 dark:text-emerald-400",
      border: "border-emerald-500/20",
      icon: CheckCircle,
    },
    degraded: {
      label: "Degraded",
      bg: "bg-amber-500/10",
      text: "text-amber-600 dark:text-amber-400",
      border: "border-amber-500/20",
      icon: AlertTriangle,
    },
    unhealthy: {
      label: "Unhealthy",
      bg: "bg-rose-500/10",
      text: "text-rose-600 dark:text-rose-400",
      border: "border-rose-500/20",
      icon: XCircle,
    },
    success: {
      label: "Success",
      bg: "bg-emerald-500/10",
      text: "text-emerald-600 dark:text-emerald-400",
      border: "border-emerald-500/20",
      icon: CheckCircle,
    },
  };

  const current: BadgeConfig = configs[normalized] ?? {
    label: agent,
    bg: "bg-slate-500/10",
    text: "text-slate-600 dark:text-slate-400",
    border: "border-slate-500/20",
    icon: HelpCircle,
  };

  const Icon = current.icon;

  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full border text-[10px] font-bold tracking-wide uppercase ${current.bg} ${current.text} ${current.border} shadow-sm`}
    >
      <Icon className="w-3 h-3" />
      {current.label}
    </span>
  );
};
