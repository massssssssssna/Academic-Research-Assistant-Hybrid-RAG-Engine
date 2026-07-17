// ─────────────────────────────────────────────────────────────────────────────
// components/Sidebar.tsx
// Left navigation panel showing the list of chat sessions.
// Contains: logo, "New Session" button, scrollable session cards, Qdrant badge.
// NOTE: Uses ONLY custom CSS classes from globals.css — no Tailwind utilities.
// ─────────────────────────────────────────────────────────────────────────────

"use client";

import type { ChatSession } from "@/types";
import { formatDate, truncate } from "@/lib/utils";

interface SidebarProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onReindex: () => void;
  isIndexing: boolean;
}

export default function Sidebar({
  sessions,
  activeSessionId,
  onSelect,
  onNew,
  onDelete,
  onReindex,
  isIndexing
}: SidebarProps) {
  return (
    <aside className="sidebar" role="navigation" aria-label="Chat sessions">
      {/* ── Logo ─────────────────────────────────────────────────────────── */}
      <div className="sidebar-logo">
        <div className="logo-icon-wrap">⚛</div>
        <div className="logo-text-wrap">
          <span className="logo-name">ResearchAI</span>
          <span className="logo-tagline">Academic Assistant</span>
        </div>
      </div>

      {/* ── New Session button ──────────────────────────────────────────── */}
      <button
        id="new-session-btn"
        className="new-session-btn"
        onClick={onNew}
        aria-label="Start a new chat session"
      >
        <span className="new-session-plus" aria-hidden="true">＋</span>
        New Session
      </button>

      {/* ── Session list heading ────────────────────────────────────────── */}
      <div className="sessions-heading" aria-hidden="true">
        RECENT SESSIONS
      </div>

      {/* ── Scrollable session cards ─────────────────────────────────────── */}
      <div className="sessions-scroll" role="list">
        {sessions.length === 0 ? (
          <p className="no-sessions-msg">No sessions yet — start one above!</p>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              className={`session-card ${activeSessionId === session.id ? "session-card-active" : ""}`}
              onClick={() => onSelect(session.id)}
              role="listitem"
              tabIndex={0}
              aria-current={activeSessionId === session.id ? "page" : undefined}
              onKeyDown={(e) => e.key === "Enter" && onSelect(session.id)}
            >
              {/* Title row + delete button */}
              <div className="session-card-header">
                <span className="session-card-title">
                  {truncate(session.title, 26)}
                </span>
                <button
                  className="session-delete-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(session.id);
                  }}
                  aria-label={`Delete session: ${session.title}`}
                  title="Delete session"
                >
                  ×
                </button>
              </div>

              {/* PDF badge — only shown when a PDF is indexed */}
              {session.pdfName && (
                <span className="session-pdf-badge">
                  📄 {truncate(session.pdfName, 22)}
                </span>
              )}

              {/* Metadata row */}
              <div className="session-meta-row">
                <span className="session-date">{formatDate(session.updatedAt)}</span>
                <span className="session-msg-count">
                  {session.messages.length} msg{session.messages.length !== 1 ? "s" : ""}
                </span>
              </div>
            </div>
          ))
        )}
      </div>

      {/* ── Re-Index Button ────────────────────────────────────────────────── */}
      <div className="sidebar-reindex-wrap">
        <button
          id="reindex-btn"
          className={isIndexing ? "sidebar-reindex-btn sidebar-reindex-btn--busy" : "sidebar-reindex-btn"}
          onClick={onReindex}
          disabled={isIndexing}
          aria-label="Initialize or re-index data"
        >
          {isIndexing ? (
            <>
              <span className="sidebar-reindex-spinner" aria-hidden="true" />
              Indexing…
            </>
          ) : (
            <>
              <svg
                className="sidebar-reindex-icon"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              Initialize / Re-Index Data
            </>
          )}
        </button>
      </div>

      {/* ── Footer: Qdrant connection badge ───────────────────────────── */}
      <div className="sidebar-qdrant-wrap">
        <div className="sidebar-qdrant-badge">
          <span aria-hidden="true">🔷</span>
          <div className="sidebar-qdrant-text">
            <div className="sidebar-qdrant-title">Qdrant Cloud</div>
            <div className="sidebar-qdrant-sub">Vector DB</div>
          </div>
          <span className="sidebar-qdrant-dot" aria-label="Connected" />
        </div>
      </div>
    </aside>
  );
}
