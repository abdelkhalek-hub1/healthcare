import React from "react";
import { ChatMessage } from "../types";
import { FeedbackRating } from "./FeedbackRating";
import { StatusBadge } from "./StatusBadge";
import {
  Calendar,
  FileCheck,
  Clock,
  ShieldAlert,
  Activity,
  Cpu,
  Bot,
  User,
} from "lucide-react";

interface MessageBubbleProps {
  message: ChatMessage;
  onFeedbackSubmit?: (correlationId: string, rating: number, comment?: string | null) => Promise<void>;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  onFeedbackSubmit,
}) => {
  const isUser = message.role === "user";
  const intent = message.intent;
  const agent = message.agent;
  const data = message.data;

  // Render structured payloads depending on classified intent
  const renderStructuredData = () => {
    if (!data) return null;

    switch (intent) {
      case "consultation":
        return (
          <div className="mt-4 p-4 rounded-xl border border-blue-100 dark:border-blue-950 bg-blue-50/50 dark:bg-blue-950/10 space-y-3">
            <h4 className="text-xs font-bold text-blue-800 dark:text-blue-300 uppercase tracking-wider flex items-center gap-1.5">
              <Calendar className="w-4 h-4" />
              Appointment Scheduling Details
            </h4>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-slate-400 dark:text-slate-500 block">Patient Name</span>
                <span className="font-semibold text-slate-700 dark:text-dark-text">{data.patient_name || "Not provided"}</span>
              </div>
              <div>
                <span className="text-slate-400 dark:text-slate-500 block">Medical Specialty</span>
                <span className="font-semibold text-slate-700 dark:text-dark-text capitalize">{data.specialty || "Not provided"}</span>
              </div>
              <div>
                <span className="text-slate-400 dark:text-slate-500 block">Location (City)</span>
                <span className="font-semibold text-slate-700 dark:text-dark-text">{data.city || "Not provided"}</span>
              </div>
              <div>
                <span className="text-slate-400 dark:text-slate-500 block">Preferred Date</span>
                <span className="font-semibold text-slate-700 dark:text-dark-text">{data.preferred_date || "Not provided"}</span>
              </div>
            </div>
            {data.doctor_preference && (
              <div className="pt-2 border-t border-blue-100/60 dark:border-blue-950/30 text-xs">
                <span className="text-slate-400 dark:text-slate-500">Doctor Preference:</span>{" "}
                <span className="font-semibold text-slate-700 dark:text-dark-text">{data.doctor_preference}</span>
              </div>
            )}
          </div>
        );

      case "reimbursement":
        return (
          <div className="mt-4 p-4 rounded-xl border border-emerald-100 dark:border-emerald-950 bg-emerald-50/30 dark:bg-emerald-950/5 space-y-4">
            <h4 className="text-xs font-bold text-emerald-800 dark:text-emerald-300 uppercase tracking-wider flex items-center gap-1.5">
              <FileCheck className="w-4 h-4" />
              Reimbursement Policy Summary
            </h4>
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div>
                <span className="text-slate-400 dark:text-slate-500 block">Coverage Details</span>
                <span className="font-semibold text-slate-700 dark:text-dark-text">{data.coverage}</span>
              </div>
              <div>
                <span className="text-slate-400 dark:text-slate-500 block flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" /> Est. Refund Delay
                </span>
                <span className="font-semibold text-slate-700 dark:text-dark-text">{data.delay}</span>
              </div>
            </div>

            {data.required_documents?.length > 0 && (
              <div className="space-y-1.5">
                <span className="text-xs font-semibold text-slate-400 dark:text-slate-500 block">Required Supporting Documents</span>
                <ul className="space-y-1">
                  {data.required_documents.map((doc: string, idx: number) => (
                    <li key={idx} className="text-xs text-slate-600 dark:text-slate-300 flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                      {doc}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {data.steps?.length > 0 && (
              <div className="space-y-1.5 pt-2 border-t border-emerald-100/50 dark:border-emerald-950/20">
                <span className="text-xs font-semibold text-slate-400 dark:text-slate-500 block">Filing Instructions</span>
                <ol className="space-y-1 list-decimal list-inside text-xs text-slate-600 dark:text-slate-300">
                  {data.steps.map((step: string, idx: number) => (
                    <span key={idx} className="block">
                      {idx + 1}. {step}
                    </span>
                  ))}
                </ol>
              </div>
            )}
          </div>
        );

      case "followup":
        return (
          <div className="mt-4 p-4 rounded-xl border border-amber-100 dark:border-amber-950 bg-amber-50/30 dark:bg-amber-950/5 space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-amber-800 dark:text-amber-300 uppercase tracking-wider flex items-center gap-1.5">
                <Activity className="w-4 h-4" />
                Symptom Tracking & Recommendations
              </h4>
              {data.requires_urgent_care && (
                <span className="px-2.5 py-1 rounded-full bg-rose-500/10 dark:bg-rose-500/20 text-rose-600 dark:text-rose-400 font-bold text-[10px] tracking-wide flex items-center gap-1 animate-pulse">
                  <ShieldAlert className="w-3.5 h-3.5" /> URGENT CARE REQUIRED
                </span>
              )}
            </div>

            {data.symptoms?.length > 0 && (
              <div>
                <span className="text-[11px] font-semibold text-slate-400 dark:text-slate-500 block mb-1">Identified Symptoms</span>
                <div className="flex flex-wrap gap-1.5">
                  {data.symptoms.map((symptom: string, idx: number) => (
                    <span
                      key={idx}
                      className="px-2.5 py-0.5 rounded-md bg-amber-100/50 dark:bg-amber-950/30 text-amber-800 dark:text-amber-300 text-xs font-medium"
                    >
                      {symptom}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {data.recommendations?.length > 0 && (
              <div className="space-y-1.5 pt-2 border-t border-amber-100/50 dark:border-amber-950/20">
                <span className="text-xs font-semibold text-slate-400 dark:text-slate-500 block">Care Guidelines</span>
                <ul className="space-y-1 text-xs text-slate-600 dark:text-slate-300">
                  {data.recommendations.map((rec: string, idx: number) => (
                    <li key={idx} className="flex items-start gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 flex-shrink-0"></span>
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className={`flex gap-4 w-full ${isUser ? "justify-end" : "justify-start"}`}>
      {/* Sender Icon Badge */}
      {!isUser && (
        <div className="w-10 h-10 rounded-xl bg-slate-100 dark:bg-dark-border border border-slate-200 dark:border-dark-border/60 flex items-center justify-center text-slate-600 dark:text-slate-300 flex-shrink-0">
          <Bot className="w-5.5 h-5.5" />
        </div>
      )}

      {/* Message Bubble Content */}
      <div className="max-w-[70%] space-y-1">
        {/* Header Metadata (AI only) */}
        {!isUser && (
          <div className="flex items-center gap-2 mb-1 px-1">
            <span className="text-[11px] font-bold text-slate-500 dark:text-slate-400">
              {agent || "Healthcare Assistant"}
            </span>
            {intent && <StatusBadge agent={intent} />}
          </div>
        )}

        {/* Text Area Card */}
        <div
          className={`px-5 py-3.5 rounded-2xl shadow-sm ${
            isUser
              ? "bg-brand-600 text-white rounded-tr-none"
              : "bg-white dark:bg-dark-card border border-slate-200 dark:border-dark-border rounded-tl-none text-slate-800 dark:text-dark-text"
          }`}
        >
          {/* Main Prose Text */}
          <div className="text-sm leading-relaxed whitespace-pre-wrap Outfit">
            {message.content}
          </div>

          {/* Structured UI Cards */}
          {!isUser && renderStructuredData()}
        </div>

        {/* Telemetry metadata footer (Assistant only) */}
        {!isUser && (
          <div className="flex items-center justify-between px-1.5 pt-1.5">
            <div className="flex items-center gap-3 text-[10px] text-slate-400 dark:text-slate-500">
              {message.timestamp && (
                <span>
                  {new Date(message.timestamp).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              )}
              {message.token_usage && (
                <span className="flex items-center gap-0.5">
                  <Cpu className="w-3 h-3" />
                  {message.token_usage.total_tokens} tokens
                </span>
              )}
            </div>

            {/* Response Rating collector */}
            {message.correlation_id && onFeedbackSubmit && (
              <FeedbackRating
                correlationId={message.correlation_id}
                onFeedbackSubmit={onFeedbackSubmit}
                savedFeedback={message.metadata?.feedback}
              />
            )}
          </div>
        )}

        {isUser && (
          <div className="text-right px-1 text-[10px] text-slate-400 dark:text-slate-500">
            {message.timestamp && (
              <span>
                {new Date(message.timestamp).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
            )}
          </div>
        )}
      </div>

      {isUser && (
        <div className="w-10 h-10 rounded-xl bg-brand-500/10 dark:bg-brand-500/20 border border-brand-500/20 flex items-center justify-center text-brand-600 dark:text-brand-400 flex-shrink-0">
          <User className="w-5.5 h-5.5" />
        </div>
      )}
    </div>
  );
};
