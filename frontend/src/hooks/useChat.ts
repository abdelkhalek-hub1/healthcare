import { useState, useEffect, useCallback } from "react";
import { ChatMessage } from "../types";
import { chatService, sessionService } from "../services/api";
import { useApp } from "../context/AppContext";

export const useChat = () => {
  const { currentSessionId, setCurrentSessionId, refreshSessions } = useApp();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load message history when session changes
  const loadHistory = useCallback(async (sessionId: string) => {
    setLoading(true);
    setError(null);
    try {
      const history = await sessionService.getSessionHistory(sessionId, 50);
      setMessages(history);
    } catch (err: any) {
      console.error("Failed to load history:", err);
      setError("Failed to load chat history.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (currentSessionId) {
      loadHistory(currentSessionId);
    } else {
      setMessages([]);
    }
  }, [currentSessionId, loadHistory]);

  // Send a new message
  const sendMessage = async (text: string) => {
    if (!text.trim()) return;

    setError(null);
    setLoading(true);

    // optimistic user message append
    const tempUserMsg: ChatMessage = {
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
      session_id: currentSessionId || "",
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const data = await chatService.sendMessage(text, currentSessionId);
      
      // Update session ID if a new one was generated
      if (!currentSessionId && data.session_id) {
        setCurrentSessionId(data.session_id);
        await refreshSessions();
      }

      // Replace optimistic message and append assistant response
      // But actually it's easier to reload history or merge. Let's merge:
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: data.answer,
        timestamp: data.timestamp || new Date().toISOString(),
        correlation_id: data.correlation_id,
        intent: data.intent,
        agent: data.agent,
        token_usage: data.token_usage,
        data: data.data,
        session_id: data.session_id,
      };

      setMessages((prev) => {
        // remove the optimistic message if it was sessionless, and reload history
        return [...prev.slice(0, prev.length - 1), { ...tempUserMsg, session_id: data.session_id }, assistantMsg];
      });
      await refreshSessions();
    } catch (err: any) {
      console.error("Chat error:", err);
      const errMsg = err.response?.data?.message || "Failed to contact assistant. Please try again.";
      setError(errMsg);
      // Remove the optimistic message on failure so the user knows it failed
      setMessages((prev) => prev.slice(0, prev.length - 1));
    } finally {
      setLoading(false);
    }
  };

  // Submit feedback rating
  const submitFeedback = async (correlationId: string, rating: number, comment?: string | null) => {
    try {
      await chatService.submitFeedback(correlationId, rating, comment);
      
      // update state locally to show feedback was registered
      setMessages((prev) =>
        prev.map((msg) =>
          msg.correlation_id === correlationId
            ? { ...msg, metadata: { ...msg.metadata, feedback: { rating, comment } } }
            : msg
        )
      );
    } catch (err) {
      console.error("Failed to submit feedback:", err);
      throw err;
    }
  };

  return {
    messages,
    loading,
    error,
    sendMessage,
    submitFeedback,
    clearChat: () => setCurrentSessionId(null),
  };
};
