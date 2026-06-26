import React, { useState } from "react";
import { ThumbsUp, ThumbsDown, Send, Check } from "lucide-react";

interface FeedbackRatingProps {
  correlationId: string;
  onFeedbackSubmit: (correlationId: string, rating: number, comment?: string | null) => Promise<void>;
  savedFeedback?: {
    rating: number;
    comment?: string | null;
  };
}

export const FeedbackRating: React.FC<FeedbackRatingProps> = ({
  correlationId,
  onFeedbackSubmit,
  savedFeedback,
}) => {
  const [rating, setRating] = useState<number | null>(savedFeedback?.rating ?? null);
  const [showComment, setShowComment] = useState(false);
  const [comment, setComment] = useState(savedFeedback?.comment ?? "");
  const [submitted, setSubmitted] = useState(!!savedFeedback);
  const [loading, setLoading] = useState(false);

  const handleRate = async (val: number) => {
    if (submitted) return;
    setRating(val);
    if (val === 1) {
      // Thumbs up submits immediately
      setLoading(true);
      try {
        await onFeedbackSubmit(correlationId, 1, null);
        setSubmitted(true);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    } else {
      // Thumbs down opens comment box
      setShowComment(true);
    }
  };

  const handleSubmitComment = async () => {
    if (rating === null || loading) return;
    setLoading(true);
    try {
      await onFeedbackSubmit(correlationId, rating, comment.trim() || null);
      setSubmitted(true);
      setShowComment(false);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="flex items-center gap-1.5 text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold bg-emerald-50 dark:bg-emerald-950/20 px-2 py-0.5 rounded-full border border-emerald-100 dark:border-emerald-950/40">
        <Check className="w-3.5 h-3.5" />
        Feedback saved
      </div>
    );
  }

  return (
    <div className="relative">
      <div className="flex items-center gap-1 bg-slate-50 dark:bg-dark-input border border-slate-200 dark:border-dark-border px-1.5 py-0.5 rounded-full">
        {/* Thumbs Up Button */}
        <button
          onClick={() => handleRate(1)}
          disabled={loading}
          className={`p-1 rounded-full hover:bg-slate-200 dark:hover:bg-dark-border transition-colors ${
            rating === 1 ? "text-emerald-500" : "text-slate-400 hover:text-slate-700"
          }`}
          title="Helpful"
        >
          <ThumbsUp className="w-3 h-3" />
        </button>

        {/* Thumbs Down Button */}
        <button
          onClick={() => handleRate(0)}
          disabled={loading}
          className={`p-1 rounded-full hover:bg-slate-200 dark:hover:bg-dark-border transition-colors ${
            rating === 0 ? "text-rose-500" : "text-slate-400 hover:text-slate-700"
          }`}
          title="Not helpful"
        >
          <ThumbsDown className="w-3 h-3" />
        </button>
      </div>

      {/* Expanded Comment Box for thumbs down */}
      {showComment && (
        <div className="absolute right-0 bottom-7 bg-white dark:bg-dark-card border border-slate-200 dark:border-dark-border p-2.5 rounded-xl shadow-lg w-64 z-20 space-y-2">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide block">
            How can we improve?
          </span>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Add comments or corrections..."
            className="w-full h-16 p-1.5 rounded-lg border border-slate-200 dark:border-dark-border bg-slate-50 dark:bg-dark-input text-xs text-slate-800 dark:text-dark-text placeholder-slate-400 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 resize-none"
          />
          <div className="flex justify-end gap-1.5">
            <button
              onClick={() => setShowComment(false)}
              className="px-2 py-1 rounded-md hover:bg-slate-100 dark:hover:bg-dark-border text-[10px] font-medium text-slate-500 dark:text-slate-400"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmitComment}
              disabled={loading}
              className="px-2.5 py-1 rounded-md bg-brand-600 hover:bg-brand-500 text-[10px] font-semibold text-white flex items-center gap-1 shadow-sm active:scale-95 transition-transform"
            >
              <Send className="w-3 h-3" /> Submit
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
