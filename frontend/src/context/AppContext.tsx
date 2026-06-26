import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { Session } from "../types";
import { sessionService } from "../services/api";

interface AppContextType {
  currentSessionId: string | null;
  setCurrentSessionId: (id: string | null) => void;
  darkMode: boolean;
  setDarkMode: (dark: boolean) => void;
  sessions: Session[];
  loadingSessions: boolean;
  refreshSessions: () => Promise<void>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(() => {
    return localStorage.getItem("current_session_id");
  });

  const [darkMode, setDarkMode] = useState<boolean>(() => {
    return localStorage.getItem("theme") === "dark";
  });

  const [sessions, setSessions] = useState<Session[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(false);

  // Sync session ID to localStorage
  useEffect(() => {
    if (currentSessionId) {
      localStorage.setItem("current_session_id", currentSessionId);
    } else {
      localStorage.removeItem("current_session_id");
    }
  }, [currentSessionId]);

  // Sync theme class to root html element
  useEffect(() => {
    const root = window.document.documentElement;
    if (darkMode) {
      root.classList.add("dark");
      localStorage.setItem("theme", "dark");
    } else {
      root.classList.remove("dark");
      localStorage.setItem("theme", "light");
    }
  }, [darkMode]);

  const refreshSessions = useCallback(async () => {
    setLoadingSessions(true);
    try {
      const data = await sessionService.getSessions(20);
      setSessions(data);
    } catch (err) {
      console.error("Failed to load sessions:", err);
    } finally {
      setLoadingSessions(false);
    }
  }, []);

  // Initial sessions load
  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  return (
    <AppContext.Provider
      value={{
        currentSessionId,
        setCurrentSessionId,
        darkMode,
        setDarkMode,
        sessions,
        loadingSessions,
        refreshSessions,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error("useApp must be used within an AppProvider");
  }
  return context;
};
