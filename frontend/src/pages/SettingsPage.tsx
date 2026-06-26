import React from "react";
import {
  Settings,
  Server,
  Shield,
  Palette,
  ToggleLeft,
  ToggleRight,
  Sun,
  Moon,
  Info,
} from "lucide-react";
import { useApp } from "../context/AppContext";

interface SettingRowProps {
  label: string;
  description: string;
  children: React.ReactNode;
}

const SettingRow: React.FC<SettingRowProps> = ({
  label,
  description,
  children,
}) => (
  <div className="flex items-center justify-between py-4 border-b border-slate-100 dark:border-dark-border/60 last:border-0">
    <div className="max-w-xs">
      <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">
        {label}
      </p>
      <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
        {description}
      </p>
    </div>
    <div className="flex-shrink-0">{children}</div>
  </div>
);

interface SectionProps {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}

const Section: React.FC<SectionProps> = ({ title, icon, children }) => (
  <div className="bg-white dark:bg-dark-card rounded-2xl border border-slate-200 dark:border-dark-border p-6">
    <div className="flex items-center gap-2 mb-5">
      <div className="w-8 h-8 rounded-lg bg-brand-50 dark:bg-brand-950/20 flex items-center justify-center text-brand-600 dark:text-brand-400">
        {icon}
      </div>
      <h3 className="font-bold text-slate-800 dark:text-dark-text text-sm">
        {title}
      </h3>
    </div>
    <div>{children}</div>
  </div>
);

export const SettingsPage: React.FC = () => {
  const { darkMode, setDarkMode } = useApp();

  return (
    <div className="p-8 space-y-8 max-w-3xl mx-auto">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-slate-800 dark:text-dark-text tracking-tight">
          Configuration & Settings
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Application preferences and system configuration
        </p>
      </div>

      {/* Appearance */}
      <Section title="Appearance" icon={<Palette className="w-4 h-4" />}>
        <SettingRow
          label="Dark Mode"
          description="Switch between light and dark interface themes"
        >
          <button
            id="dark-mode-toggle"
            onClick={() => setDarkMode(!darkMode)}
            className="flex items-center gap-2.5 px-4 py-2 rounded-xl border border-slate-200 dark:border-dark-border bg-slate-50 dark:bg-dark-input text-slate-700 dark:text-slate-200 text-sm font-medium hover:bg-slate-100 dark:hover:bg-dark-border transition-all duration-200 active:scale-95"
          >
            {darkMode ? (
              <>
                <Sun className="w-4 h-4 text-amber-500" />
                Light Mode
              </>
            ) : (
              <>
                <Moon className="w-4 h-4 text-indigo-500" />
                Dark Mode
              </>
            )}
          </button>
        </SettingRow>
        <SettingRow
          label="Font"
          description="UI uses Outfit with Inter fallback for maximum readability"
        >
          <span className="text-xs text-slate-400 dark:text-slate-500 font-mono bg-slate-100 dark:bg-dark-border px-3 py-1.5 rounded-lg">
            Outfit / Inter
          </span>
        </SettingRow>
      </Section>

      {/* Backend */}
      <Section title="Backend Configuration" icon={<Server className="w-4 h-4" />}>
        <SettingRow
          label="API Base URL"
          description="Requests are proxied via Vite dev server to the FastAPI backend"
        >
          <span className="text-xs font-mono text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-950/20 border border-brand-200 dark:border-brand-800/40 px-3 py-1.5 rounded-lg">
            /api/v1
          </span>
        </SettingRow>
        <SettingRow
          label="LLM Provider"
          description="Language model driving all AI agents"
        >
          <span className="text-xs font-semibold text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-dark-border px-3 py-1.5 rounded-lg">
            Groq (llama3-8b-8192)
          </span>
        </SettingRow>
        <SettingRow
          label="Orchestration"
          description="LangGraph StateGraph router pattern"
        >
          <span className="text-xs font-semibold text-violet-600 dark:text-violet-400 bg-violet-50 dark:bg-violet-950/20 border border-violet-200 dark:border-violet-800/40 px-3 py-1.5 rounded-lg">
            LangGraph Router
          </span>
        </SettingRow>
        <SettingRow
          label="Database"
          description="Conversation history and telemetry persistence"
        >
          <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800/40 px-3 py-1.5 rounded-lg">
            MongoDB (Motor)
          </span>
        </SettingRow>
      </Section>

      {/* Features */}
      <Section title="Feature Flags" icon={<ToggleLeft className="w-4 h-4" />}>
        {[
          { label: "Structured Agent Outputs", desc: "Pydantic-validated JSON responses from all agents", enabled: true },
          { label: "LangSmith Tracing", desc: "Execution traces forwarded to LangSmith if LANGCHAIN_API_KEY is set", enabled: true },
          { label: "Correlation ID Tracking", desc: "Every request tagged with a unique correlation ID", enabled: true },
          { label: "Session Persistence", desc: "Conversation history persisted to MongoDB", enabled: true },
          { label: "Feedback Collection", desc: "Thumbs up/down ratings stored per AI response turn", enabled: true },
        ].map((feat) => (
          <SettingRow key={feat.label} label={feat.label} description={feat.desc}>
            <div className="flex items-center gap-1.5">
              {feat.enabled ? (
                <ToggleRight className="w-6 h-6 text-emerald-500" />
              ) : (
                <ToggleLeft className="w-6 h-6 text-slate-300 dark:text-slate-600" />
              )}
              <span
                className={`text-xs font-semibold ${
                  feat.enabled
                    ? "text-emerald-600 dark:text-emerald-400"
                    : "text-slate-400 dark:text-slate-500"
                }`}
              >
                {feat.enabled ? "Enabled" : "Disabled"}
              </span>
            </div>
          </SettingRow>
        ))}
      </Section>

      {/* Privacy */}
      <Section title="Privacy & Compliance" icon={<Shield className="w-4 h-4" />}>
        <SettingRow
          label="Data Residency"
          description="All data is processed and stored locally"
        >
          <span className="text-xs font-semibold text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-dark-border px-3 py-1.5 rounded-lg">
            On-Premise
          </span>
        </SettingRow>
        <SettingRow
          label="Medical Disclaimer"
          description="This assistant is informational only, not a substitute for professional medical advice"
        >
          <div className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400">
            <Info className="w-4 h-4" />
            <span className="text-xs font-semibold">Informational Only</span>
          </div>
        </SettingRow>
      </Section>

      {/* About */}
      <div className="text-center py-4 text-xs text-slate-400 dark:text-slate-500 space-y-1">
        <p className="font-semibold text-slate-600 dark:text-slate-400">
          Healthcare AI Router v1.0.0
        </p>
        <p>
          Multi-Agent · LangGraph Router · FastAPI · MongoDB · Groq
        </p>
        <p className="flex items-center justify-center gap-1">
          <Settings className="w-3 h-3" />
          Enterprise-grade healthcare AI architecture
        </p>
      </div>
    </div>
  );
};
