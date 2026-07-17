// ─────────────────────────────────────────────────────────────────────────────
// components/ChatArea.tsx
// The main center content: scrollable messages viewport + fixed bottom input bar.
// Decides what to render based on session/PDF/indexing state:
//   1. No PDF & no messages → EmptyState (dropzone)
//   2. isIndexing & no messages → EmptyState (indexing spinner)
//   3. Has messages → message list + optional loading bubbles
// ─────────────────────────────────────────────────────────────────────────────

"use client";

import { useEffect, useRef } from "react";
import type { ChatSession } from "@/types";
import MessageBubble from "./MessageBubble";
import EmptyState from "./EmptyState";
import LoadingBubble from "./LoadingBubble";

interface ChatAreaProps {
  session: ChatSession | null;
  inputValue: string;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onFileSelect: (file: File) => void;
  isLoading: boolean;
  isIndexing: boolean;
  topK: number;
}

export default function ChatArea({
  session,
  inputValue,
  onInputChange,
  onSend,
  onFileSelect,
  isLoading,
  isIndexing,
  topK,
}: ChatAreaProps) {
  const bottomAnchorRef = useRef<HTMLDivElement>(null);

  // Derived state
  const hasMessages = (session?.messages?.length ?? 0) > 0;
  const showDropzone = !isIndexing && !hasMessages;
  const showIndexingSpinner = isIndexing && !hasMessages;

  // ── Auto-scroll to bottom whenever messages update ─────────────────────
  useEffect(() => {
    bottomAnchorRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.messages, isLoading, isIndexing]);

  // ── Keyboard: Enter sends, Shift+Enter inserts newline ─────────────────
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="chat-area flex-1 flex flex-col relative h-full">
      {/* ── Active Model Header ────────────────────────────────────────── */}
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

      {/* ── Messages viewport ──────────────────────────────────────────── */}
      <div className="messages-viewport flex-1 overflow-y-auto">
        {showDropzone ? (
          // Case 1: No PDF yet — show the drag-and-drop zone
          <EmptyState onFileSelect={onFileSelect} isIndexing={false} />
        ) : showIndexingSpinner ? (
          // Case 2: PDF chosen, indexing in progress (no messages yet)
          <EmptyState onFileSelect={onFileSelect} isIndexing={true} />
        ) : (
          // Case 3: Messages exist — render chat bubbles
          <>
            {session?.messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}

            {/* Indexing bubble: shown when replacing a PDF on a session that already has messages */}
            {isIndexing && (
              <LoadingBubble text="Indexing into Qdrant Cloud…" />
            )}

            {/* RAG loading bubble: shown while waiting for LLM response */}
            {isLoading && (
              <LoadingBubble text="Searching Qdrant & Synthesizing response…" />
            )}

            {/* Invisible anchor div for auto-scroll */}
            <div ref={bottomAnchorRef} aria-hidden="true" />
          </>
        )}
      </div>

      {/* ── Fixed bottom input bar ──────────────────────────────────────── */}
      <div className="input-bar">
        <div className="input-wrapper">
          <textarea
            id="chat-input"
            className="chat-textarea"
            placeholder={
              isIndexing
                ? "Indexing documents…"
                : "Ask a research question…  (Enter ↵ to send, Shift+Enter for new line)"
            }
            value={inputValue}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading || isIndexing}
            rows={1}
            aria-label="Chat input"
          />

          {/* Send button */}
          <button
            id="send-message-btn"
            className="send-btn"
            onClick={onSend}
            disabled={!inputValue.trim() || isLoading || isIndexing}
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

        {/* Context hint below the input */}
        <p className="input-hint" aria-live="polite">
          Powered by Qdrant + Groq (Llama-3) · Index your data via the sidebar first
        </p>
      </div>
    </div>
  );
}
