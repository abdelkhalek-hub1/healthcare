import React, { useState } from "react";
import { AppProvider } from "./context/AppContext";
import { Sidebar } from "./components/Sidebar";
import { DashboardPage } from "./pages/DashboardPage";
import { ChatPage } from "./pages/ChatPage";
import { HistoryPage } from "./pages/HistoryPage";
import { MonitoringPage } from "./pages/MonitoringPage";
import { HealthPage } from "./pages/HealthPage";
import { SettingsPage } from "./pages/SettingsPage";

type Tab =
  | "dashboard"
  | "chat"
  | "history"
  | "monitoring"
  | "health"
  | "settings";

const AppContent: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>("dashboard");

  const renderPage = () => {
    switch (activeTab) {
      case "dashboard":
        return (
          <DashboardPage onNavigate={(tab) => setActiveTab(tab as Tab)} />
        );
      case "chat":
        return <ChatPage />;
      case "history":
        return (
          <HistoryPage onNavigateToChat={() => setActiveTab("chat")} />
        );
      case "monitoring":
        return <MonitoringPage />;
      case "health":
        return <HealthPage />;
      case "settings":
        return <SettingsPage />;
      default:
        return (
          <DashboardPage onNavigate={(tab) => setActiveTab(tab as Tab)} />
        );
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-50 dark:bg-dark-bg transition-colors duration-200">
      {/* Fixed sidebar */}
      <Sidebar activeTab={activeTab} setActiveTab={(tab) => setActiveTab(tab as Tab)} />

      {/* Main content — offset for fixed sidebar width (w-72 = 288px) */}
      <main className="flex-1 ml-72 min-h-screen overflow-hidden">
        {renderPage()}
      </main>
    </div>
  );
};

const App: React.FC = () => {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
};

export default App;
