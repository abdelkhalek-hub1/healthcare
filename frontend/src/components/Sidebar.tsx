import React from "react";
import { useApp } from "../context/AppContext";
import {
  LayoutDashboard,
  MessageSquare,
  History,
  Activity,
  HeartPulse,
  Settings,
  Sun,
  Moon,
  Plus,
  Heart,
} from "lucide-react";

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab }) => {
  const {
    currentSessionId,
    setCurrentSessionId,
    darkMode,
    setDarkMode,
    sessions,
  } = useApp();

  const navigationItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "chat", label: "AI Consultation", icon: MessageSquare },
    { id: "history", label: "Session History", icon: History },
    { id: "monitoring", label: "Telemetry logs", icon: Activity },
    { id: "health", label: "System Health", icon: HeartPulse },
    { id: "settings", label: "Config Settings", icon: Settings },
  ];

  const handleNewChat = () => {
    setCurrentSessionId(null);
    setActiveTab("chat");
  };

  return (
    <aside className="w-72 bg-white dark:bg-dark-card border-r border-slate-200 dark:border-dark-border flex flex-col h-screen fixed left-0 top-0 transition-colors duration-200 z-10">
      {/* Brand Logo Header */}
      <div className="p-6 border-b border-slate-200 dark:border-dark-border flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-brand-400 flex items-center justify-center shadow-lg shadow-brand-500/20 text-white animate-pulse-subtle">
          <Heart className="w-5.5 h-5.5 fill-white" />
        </div>
        <div>
          <h1 className="font-bold text-lg leading-tight tracking-tight text-slate-800 dark:text-dark-text Outfit">
            Healthcare Router
          </h1>
          <span className="text-[11px] font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-widest">
            Multi-Agent AI
          </span>
        </div>
      </div>

      {/* Main Action Trigger */}
      <div className="px-4 py-4">
        <button
          onClick={handleNewChat}
          className="w-full py-3 px-4 rounded-xl bg-brand-600 hover:bg-brand-500 active:bg-brand-700 text-white font-semibold text-sm flex items-center justify-center gap-2 shadow-md hover:shadow-lg shadow-brand-600/10 hover:shadow-brand-600/20 transition-all duration-200 group active:scale-[0.98]"
        >
          <Plus className="w-4 h-4 transition-transform duration-200 group-hover:rotate-90" />
          New Consultation
        </button>
      </div>

      {/* Sidebar Navigation Options */}
      <nav className="flex-1 px-3 space-y-1 overflow-y-auto">
        {navigationItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-150 ${
                isActive
                  ? "bg-brand-50 dark:bg-brand-950/30 text-brand-700 dark:text-brand-300"
                  : "text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-dark-text hover:bg-slate-50 dark:hover:bg-brand-950/10"
              }`}
            >
              <Icon className={`w-5 h-5 ${isActive ? "text-brand-600 dark:text-brand-400" : ""}`} />
              {item.label}
            </button>
          );
        })}

        {/* Recent Active Sessions Segment */}
        {sessions.length > 0 && (
          <div className="pt-6 mt-4 border-t border-slate-100 dark:border-dark-border/40">
            <span className="px-4 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block mb-2">
              Recent Consultations
            </span>
            <div className="space-y-1 px-1 max-h-56 overflow-y-auto">
              {sessions.map((sess) => (
                <button
                  key={sess.id}
                  onClick={() => {
                    setCurrentSessionId(sess.id);
                    setActiveTab("chat");
                  }}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs truncate transition-all duration-150 block ${
                    currentSessionId === sess.id
                      ? "bg-slate-100 dark:bg-dark-border text-slate-800 dark:text-dark-text font-medium"
                      : "text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-dark-text hover:bg-slate-50 dark:hover:bg-brand-950/5"
                  }`}
                >
                  {sess.last_intent ? `[${sess.last_intent.toUpperCase()}]` : "[NEW]"} {sess.id.slice(0, 8)}...
                </button>
              ))}
            </div>
          </div>
        )}
      </nav>

      {/* Dark Theme & Footer Control Segment */}
      <div className="p-4 border-t border-slate-200 dark:border-dark-border flex items-center justify-between">
        <button
          onClick={() => setDarkMode(!darkMode)}
          className="p-2 rounded-xl border border-slate-200 dark:border-dark-border bg-slate-50 dark:bg-dark-input hover:bg-slate-100 dark:hover:bg-dark-border text-slate-600 dark:text-slate-300 transition-all duration-200 active:scale-95"
          title={darkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
        >
          {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>
        <div className="text-right">
          <span className="text-[10px] text-slate-400 dark:text-slate-500 block font-medium">
            System status
          </span>
          <span className="text-[11px] font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5 justify-end">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
            Online
          </span>
        </div>
      </div>
    </aside>
  );
};
