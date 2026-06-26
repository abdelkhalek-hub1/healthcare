import React from "react";

type ColorKey =
  | "brand"
  | "emerald"
  | "amber"
  | "violet"
  | "rose"
  | "teal"
  | "blue";

const colorMap: Record<ColorKey, string> = {
  brand: "bg-brand-500/10 text-brand-600 dark:text-brand-400",
  emerald: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  amber: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  violet: "bg-violet-500/10 text-violet-600 dark:text-violet-400",
  rose: "bg-rose-500/10 text-rose-600 dark:text-rose-400",
  teal: "bg-teal-500/10 text-teal-600 dark:text-teal-400",
  blue: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
};

interface MetricCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  change?: string;
  changeType?: "positive" | "negative" | "neutral";
  /** Semantic color name or raw Tailwind class string. */
  color?: ColorKey | string;
  subtitle?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  icon,
  change,
  changeType = "neutral",
  color = "brand",
  subtitle,
}) => {
  const iconClasses =
    (colorMap as Record<string, string>)[color as string] ??
    color;

  return (
    <div className="bg-white dark:bg-dark-card border border-slate-200 dark:border-dark-border p-6 rounded-2xl shadow-sm flex items-center justify-between transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 gap-4">
      <div className="space-y-1.5 min-w-0">
        <span className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">
          {title}
        </span>
        <h3 className="text-3xl font-extrabold text-slate-800 dark:text-dark-text tracking-tight">
          {value}
        </h3>
        {subtitle && (
          <span className="text-xs text-slate-400 dark:text-slate-500 block">
            {subtitle}
          </span>
        )}
        {change && (
          <span
            className={`text-xs font-semibold ${
              changeType === "positive"
                ? "text-emerald-600 dark:text-emerald-400"
                : changeType === "negative"
                ? "text-rose-600 dark:text-rose-400"
                : "text-slate-400 dark:text-slate-500"
            }`}
          >
            {change}
          </span>
        )}
      </div>

      <div
        className={`w-14 h-14 rounded-2xl ${iconClasses} flex items-center justify-center shadow-inner flex-shrink-0`}
      >
        {icon}
      </div>
    </div>
  );
};
