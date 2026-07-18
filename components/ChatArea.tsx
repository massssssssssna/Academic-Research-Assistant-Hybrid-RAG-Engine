// ─────────────────────────────────────────────────────────────────────────────
// components/ChatArea.tsx
// The main center content: scrollable messages viewport + fixed bottom input bar.
// Knowledge base is pre-indexed — no PDF upload or EmptyState dropzone.
// Shows a "Ready" welcome state when there are no messages yet.
// ─────────────────────────────────────────────────────────────────────────────

"use client";

import { useEffect, useRef } from "react";
import type { ChatSession } from "@/types";
import MessageBubble from "./MessageBubble";
import LoadingBubble from "./LoadingBubble";

interface ChatAreaProps {
  session:       ChatSession | null;
  inputValue:    string;
  onInputChange: (value: string) => void;
  onSend:        () => void;
  isLoading:     boolean;
  topK:          number;
}

export default function ChatArea({
  session,
  inputValue,
  onInputChange,
  onSend,
  isLoading,
  topK,
}: ChatAreaProps) {
  const bottomAnchorRef = useRef<HTMLDivElement>(null);

  const hasMessages = (session?.messages?.length ?? 0) > 0;

  // ── Auto-scroll to bottom whenever messages update ────────────────────
  useEffect(() => {
    bottomAnchorRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.messages, isLoading]); // eslint-disable-line react-hooks/exhaustive-deps


  // ── Keyboard: Enter sends, Shift+Enter inserts newline ────────────────
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="chat-area flex-1 flex flex-col relative h-full">
      {/* ── Active Model Badge ────────────────────────────────────────── */}
      {hasMessages && (
        <div className="absolute top-0 left-0 right-0 z-10 flex justify-center py-2 bg-gradient-to-b from-[#111214] to-transparent pointer-events-none">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-[#1e1f22]/90 border border-white/10 rounded-full backdrop-blur-sm shadow-sm pointer-events-auto">
            <div className="w-2 h-2 rounded-full bg-green-400 shadow-[0_0_8px_rgba(74,222,128,0.6)] animate-pulse" />
            <span className="text-[11px] font-medium text-slate-300 tracking-wide">
              Llama-3 via Groq <span className="text-slate-500">|</span> Top-K: {topK}
            </span>
          </div>
        </div>
      )}

      {/* ── Messages viewport ─────────────────────────────────────────── */}
      <div className="messages-viewport flex-1 overflow-y-auto">
        {!hasMessages ? (
          /* Welcome / Ready state — knowledge base is pre-indexed */
          <div className="eval-welcome">
            <div className="eval-welcome-icon">🔬</div>
            <h2 className="eval-welcome-title">Research Assistant Ready</h2>
            <p className="eval-welcome-sub">
              Knowledge base is indexed and active. Ask any research question below.
              <br />
              Every response includes a <strong>Generation Evaluation Report</strong> with
              faithfulness, hallucination detection, and latency metrics.
            </p>
            <div className="eval-welcome-chips">
              <span className="eval-welcome-chip">📊 Faithfulness Score</span>
              <span className="eval-welcome-chip">🔍 Hallucination Detection</span>
              <span className="eval-welcome-chip">✅ Claim Verification</span>
              <span className="eval-welcome-chip">⚡ Latency Breakdown</span>
            </div>
          </div>
        ) : (
          <>
            {session?.messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}

            {/* RAG loading bubble */}
            {isLoading && (
              <LoadingBubble text="Searching Qdrant & Synthesizing response…" />
            )}

            <div ref={bottomAnchorRef} aria-hidden="true" />
          </>
        )}
      </div>

      {/* ── Fixed bottom input bar ───────────────────────────────────── */}
      <div className="input-bar">
        <div className="input-wrapper">
          <textarea
            id="chat-input"
            className="chat-textarea"
            placeholder="Ask a research question…  (Enter ↵ to send, Shift+Enter for new line)"
            value={inputValue}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={1}
            aria-label="Chat input"
          />

          <button
            id="send-message-btn"
            className="send-btn"
            onClick={onSend}
            disabled={!inputValue.trim() || isLoading}
            aria-label="Send message"
            title="Send (Enter)"
          >
            <svg
              viewBox="0 0 24 24"
              width="18"
              height="18"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>

        <p className="input-hint" aria-live="polite">
          Powered by Qdrant · Groq (Llama-3) · Generation Evaluation runs automatically after every response
        </p>
      </div>
    </div>
  );
}
