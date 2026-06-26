import React, { useEffect, useState, useCallback } from "react";
import {
  Clock,
  MessageSquare,
  ChevronRight,
  Search,
  Loader2,
  Inbox,
  RefreshCw,
} from "lucide-react";
import { Session, ChatMessage } from "../types";
import { sessionService } from "../services/api";
import { useApp } from "../context/AppContext";
import { StatusBadge } from "../components/StatusBadge";
import { MessageBubble } from "../components/MessageBubble";

interface HistoryPageProps {
  onNavigateToChat: () => void;
}

export const HistoryPage: React.FC<HistoryPageProps> = ({
  onNavigateToChat,
}) => {
  const { sessions, loadingSessions, refreshSessions, setCurrentSessionId } =
    useApp();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSession, setSelectedSession] = useState<Session | null>(null);
  const [sessionMessages, setSessionMessages] = useState<ChatMessage[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);

  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  const loadSession = useCallback(async (sess: Session) => {
    setSelectedSession(sess);
    setLoadingMessages(true);
    try {
      const msgs = await sessionService.getSessionHistory(sess.id, 100);
      setSessionMessages(msgs);
    } catch (err) {
      console.error("Failed to load session history:", err);
    } finally {
      setLoadingMessages(false);
    }
  }, []);

  const openInChat = (sessionId: string) => {
    setCurrentSessionId(sessionId);
    onNavigateToChat();
  };

  const filtered = sessions.filter(
    (s) =>
      s.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (s.last_intent ?? "").toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sessions Sidebar */}
      <div className="w-80 border-r border-slate-200 dark:border-dark-border bg-white dark:bg-dark-card flex flex-col flex-shrink-0">
        <div className="p-5 border-b border-slate-200 dark:border-dark-border">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold text-slate-800 dark:text-dark-text text-base">
              Session History
            </h2>
            <button
              onClick={refreshSessions}
              disabled={loadingSessions}
              className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-dark-border text-slate-400 transition-all duration-200 active:scale-90"
            >
              <RefreshCw
                className={`w-4 h-4 ${loadingSessions ? "animate-spin" : ""}`}
              />
            </button>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              id="session-search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search sessions..."
              className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-slate-200 dark:border-dark-border bg-slate-50 dark:bg-dark-input text-sm text-slate-700 dark:text-dark-text placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500 transition-all"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {loadingSessions && filtered.length === 0 ? (
            <div className="flex justify-center items-center py-10">
              <Loader2 className="w-6 h-6 text-brand-500 animate-spin" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 gap-3 text-slate-400 dark:text-slate-500">
              <Inbox className="w-8 h-8 opacity-40" />
              <p className="text-sm">No sessions found</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100 dark:divide-dark-border/40">
              {filtered.map((sess) => (
                <button
                  key={sess.id}
                  onClick={() => loadSession(sess)}
                  className={`w-full text-left px-5 py-4 hover:bg-slate-50 dark:hover:bg-dark-border/30 transition-all duration-150 ${
                    selectedSession?.id === sess.id
                      ? "bg-brand-50 dark:bg-brand-950/20 border-r-2 border-brand-500"
                      : ""
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <MessageSquare className="w-3.5 h-3.5 text-brand-500 flex-shrink-0" />
                        <span className="text-xs font-mono text-slate-500 dark:text-slate-400 truncate">
                          {sess.id.slice(0, 16)}…
                        </span>
                      </div>
                      {sess.last_intent && (
                        <StatusBadge agent={sess.last_intent} />
                      )}
                      <div className="flex items-center gap-3 mt-2">
                        <span className="text-[10px] text-slate-400 dark:text-slate-500 flex items-center gap-1">
                          <MessageSquare className="w-3 h-3" />
                          {sess.message_count} msgs
                        </span>
                        <span className="text-[10px] text-slate-400 dark:text-slate-500 flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatDate(sess.updated_at)}
                        </span>
                      </div>
                    </div>
                    <ChevronRight
                      className={`w-4 h-4 text-slate-300 dark:text-slate-600 flex-shrink-0 mt-1 transition-transform ${
                        selectedSession?.id === sess.id ? "rotate-90" : ""
                      }`}
                    />
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Message Viewer */}
      <div className="flex-1 flex flex-col overflow-hidden bg-slate-50 dark:bg-dark-bg">
        {!selectedSession ? (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-slate-400 dark:text-slate-500">
            <MessageSquare className="w-12 h-12 opacity-30" />
            <p className="text-sm">Select a session to view the transcript</p>
          </div>
        ) : (
          <>
            {/* Viewer Header */}
            <div className="px-8 py-4 bg-white dark:bg-dark-card border-b border-slate-200 dark:border-dark-border flex items-center justify-between flex-shrink-0">
              <div>
                <h3 className="font-bold text-slate-800 dark:text-dark-text text-sm">
                  Session{" "}
                  <span className="font-mono text-brand-600 dark:text-brand-400">
                    {selectedSession.id.slice(0, 16)}…
                  </span>
                </h3>
                <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
                  {selectedSession.message_count} messages · Started{" "}
                  {formatDate(selectedSession.created_at)}
                </p>
              </div>
              <button
                onClick={() => openInChat(selectedSession.id)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 active:bg-brand-700 text-white text-xs font-semibold shadow-sm transition-all duration-200 active:scale-95"
              >
                <MessageSquare className="w-3.5 h-3.5" />
                Continue in Chat
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-8 py-6 space-y-6">
              {loadingMessages ? (
                <div className="flex justify-center py-12">
                  <Loader2 className="w-7 h-7 text-brand-500 animate-spin" />
                </div>
              ) : sessionMessages.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-slate-400 dark:text-slate-500 gap-2">
                  <Inbox className="w-8 h-8 opacity-40" />
                  <p className="text-sm">No messages in this session</p>
                </div>
              ) : (
                sessionMessages.map((msg, idx) => (
                  <MessageBubble
                    key={`${msg.correlation_id ?? idx}-${msg.role}`}
                    message={msg}
                  />
                ))
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};
