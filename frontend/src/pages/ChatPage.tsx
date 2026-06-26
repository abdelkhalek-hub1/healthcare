import React, { useRef, useEffect } from "react";
import { Send, Loader2, AlertCircle, Sparkles } from "lucide-react";
import { MessageBubble } from "../components/MessageBubble";
import { useChat } from "../hooks/useChat";

/**
 * Full-page AI chat interface.
 * Manages send / feedback cycles and auto-scrolls the conversation area.
 */
export const ChatPage: React.FC = () => {
  const { messages, loading, error, sendMessage, submitFeedback, clearChat } =
    useChat();
  const [inputValue, setInputValue] = React.useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const trimmed = inputValue.trim();
    if (!trimmed || loading) return;
    setInputValue("");
    inputRef.current?.focus();
    await sendMessage(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const suggestedPrompts = [
    "I need to book a specialist appointment in New York",
    "How do I file a reimbursement claim for my recent visit?",
    "I've had a headache and mild fever for the past 3 days",
    "What's the coverage policy for mental health sessions?",
  ];

  return (
    <div className="flex flex-col h-screen">
      {/* Chat Header */}
      <div className="flex items-center justify-between px-8 py-5 border-b border-slate-200 dark:border-dark-border bg-white dark:bg-dark-card flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-sm">
            <Sparkles className="w-4.5 h-4.5 text-white" />
          </div>
          <div>
            <h2 className="font-bold text-slate-800 dark:text-dark-text text-sm leading-tight">
              AI Healthcare Assistant
            </h2>
            <span className="text-[11px] text-emerald-500 dark:text-emerald-400 font-semibold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping inline-block" />
              Online · LangGraph Router
            </span>
          </div>
        </div>
        <button
          onClick={clearChat}
          className="text-xs text-slate-400 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 font-medium transition-colors px-3 py-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-dark-border"
        >
          New Chat
        </button>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-8 py-6 space-y-6 bg-slate-50 dark:bg-dark-bg">
        {messages.length === 0 && !loading && (
          <div className="flex flex-col items-center justify-center h-full gap-6 py-12">
            <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-xl shadow-brand-500/20">
              <Sparkles className="w-9 h-9 text-white" />
            </div>
            <div className="text-center space-y-2">
              <h3 className="text-xl font-bold text-slate-700 dark:text-dark-text">
                Start a Consultation
              </h3>
              <p className="text-sm text-slate-400 dark:text-slate-500 max-w-sm">
                I can help with appointment scheduling, reimbursement claims,
                symptom follow-ups, and general health questions.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3 max-w-lg w-full mt-2">
              {suggestedPrompts.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => sendMessage(prompt)}
                  className="text-left px-4 py-3 rounded-xl border border-slate-200 dark:border-dark-border bg-white dark:bg-dark-card text-xs text-slate-600 dark:text-slate-300 hover:border-brand-300 hover:text-brand-700 dark:hover:text-brand-300 dark:hover:border-brand-800 transition-all duration-200 font-medium shadow-sm hover:shadow-md active:scale-[0.98]"
                >
                  "{prompt}"
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <MessageBubble
            key={`${msg.correlation_id ?? idx}-${msg.role}`}
            message={msg}
            onFeedbackSubmit={
              msg.role === "assistant" ? submitFeedback : undefined
            }
          />
        ))}

        {loading && (
          <div className="flex gap-4 w-full justify-start">
            <div className="w-10 h-10 rounded-xl bg-slate-100 dark:bg-dark-border border border-slate-200 dark:border-dark-border/60 flex items-center justify-center flex-shrink-0">
              <Loader2 className="w-5 h-5 text-brand-500 animate-spin" />
            </div>
            <div className="bg-white dark:bg-dark-card border border-slate-200 dark:border-dark-border px-5 py-3.5 rounded-2xl rounded-tl-none shadow-sm">
              <div className="flex gap-1.5 items-center h-5">
                <span className="w-2 h-2 rounded-full bg-brand-400 animate-bounce [animation-delay:0ms]" />
                <span className="w-2 h-2 rounded-full bg-brand-400 animate-bounce [animation-delay:150ms]" />
                <span className="w-2 h-2 rounded-full bg-brand-400 animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-800/40 text-rose-700 dark:text-rose-400 text-sm">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input Bar */}
      <div className="px-8 py-5 border-t border-slate-200 dark:border-dark-border bg-white dark:bg-dark-card flex-shrink-0">
        <div className="flex gap-3 items-end max-w-4xl mx-auto">
          <textarea
            ref={inputRef}
            id="chat-input"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your healthcare question… (Enter to send, Shift+Enter for newline)"
            rows={1}
            style={{ resize: "none" }}
            className="flex-1 px-5 py-3.5 rounded-2xl border border-slate-200 dark:border-dark-border bg-slate-50 dark:bg-dark-input text-sm text-slate-800 dark:text-dark-text placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500 dark:focus:border-brand-600 transition-all duration-200 leading-relaxed"
            onInput={(e) => {
              const t = e.target as HTMLTextAreaElement;
              t.style.height = "auto";
              t.style.height = `${Math.min(t.scrollHeight, 140)}px`;
            }}
          />
          <button
            id="chat-send-btn"
            onClick={handleSend}
            disabled={!inputValue.trim() || loading}
            className="w-12 h-12 rounded-2xl bg-brand-600 hover:bg-brand-500 active:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed text-white flex items-center justify-center shadow-md hover:shadow-lg shadow-brand-600/20 transition-all duration-200 active:scale-95 flex-shrink-0"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
        <p className="text-center text-[10px] text-slate-400 dark:text-slate-500 mt-2">
          This assistant is for informational purposes only. Always consult a
          licensed medical professional.
        </p>
      </div>
    </div>
  );
};
