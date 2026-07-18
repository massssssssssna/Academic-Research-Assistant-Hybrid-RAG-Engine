// ─────────────────────────────────────────────────────────────────────────────
// components/Header.tsx
// Top bar of the center workspace.
// Shows: session title · Qdrant status · Clear button
// PDF upload removed — knowledge base is pre-indexed.
// ─────────────────────────────────────────────────────────────────────────────

"use client";

import type { ChatSession } from "@/types";

interface HeaderProps {
  session:    ChatSession | null;
  onClearChat: () => void;
}

export default function Header({ session, onClearChat }: HeaderProps) {
  return (
    <header className="app-header" role="banner">
      {/* ── Left: session title ──────────────────────────────────────────── */}
      <div className="header-left">
        {session ? (
          <>
            <span className="header-session-dot" aria-hidden="true">💬</span>
            <h1 className="header-session-title">{session.title}</h1>
          </>
        ) : (
          <h1 className="header-session-title">Academic &amp; Research Assistant</h1>
        )}
      </div>

      {/* ── Right: controls ─────────────────────────────────────────────── */}
      <div className="header-right">
        {/* Qdrant live indicator */}
        <div className="header-qdrant-status" aria-label="Qdrant connected">
          <span className="header-status-dot" />
          <span className="header-status-label">Qdrant</span>
        </div>

        {/* Knowledge base badge */}
        <div className="header-kb-badge">
          <span aria-hidden="true">📚</span>
          <span>Knowledge Base Active</span>
        </div>

        {/* Clear chat — only shown when session has messages */}
        {session && session.messages.length > 0 && (
          <button
            id="header-clear-btn"
            className="header-clear-btn"
            onClick={onClearChat}
            aria-label="Clear all messages in this session"
          >
            🗑 Clear
          </button>
        )}
      </div>
    </header>
  );
}
