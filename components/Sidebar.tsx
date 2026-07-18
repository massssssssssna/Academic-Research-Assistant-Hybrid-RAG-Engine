// ─────────────────────────────────────────────────────────────────────────────
// components/Sidebar.tsx
// Left navigation panel.
// Contains: logo, "New Session" button, session list, Eval Test Suite button.
// PDF upload and Re-Index removed — knowledge base is pre-indexed.
// ─────────────────────────────────────────────────────────────────────────────

"use client";

import type { ChatSession } from "@/types";
import { formatDate, truncate } from "@/lib/utils";

interface SidebarProps {
  sessions:        ChatSession[];
  activeSessionId: string | null;
  onSelect:        (id: string) => void;
  onNew:           () => void;
  onDelete:        (id: string) => void;
  onOpenTestPanel: () => void;
}

export default function Sidebar({
  sessions,
  activeSessionId,
  onSelect,
  onNew,
  onDelete,
  onOpenTestPanel,
}: SidebarProps) {
  return (
    <aside className="sidebar" role="navigation" aria-label="Chat sessions">
      {/* ── Logo ──────────────────────────────────────────────────────── */}
      <div className="sidebar-logo">
        <div className="logo-icon-wrap">⚛</div>
        <div className="logo-text-wrap">
          <span className="logo-name">ResearchAI</span>
          <span className="logo-tagline">Academic Assistant</span>
        </div>
      </div>

      {/* ── New Session ───────────────────────────────────────────────── */}
      <button
        id="new-session-btn"
        className="new-session-btn"
        onClick={onNew}
        aria-label="Start a new chat session"
      >
        <span className="new-session-plus" aria-hidden="true">＋</span>
        New Session
      </button>

      {/* ── Knowledge Base Status Badge ───────────────────────────────── */}
      <div className="sidebar-kb-status">
        <span className="sidebar-kb-dot" />
        <span className="sidebar-kb-label">Knowledge Base Indexed</span>
      </div>

      {/* ── Session list ──────────────────────────────────────────────── */}
      <div className="sessions-heading" aria-hidden="true">RECENT SESSIONS</div>

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
              <div className="session-card-header">
                <span className="session-card-title">{truncate(session.title, 26)}</span>
                <button
                  className="session-delete-btn"
                  onClick={(e) => { e.stopPropagation(); onDelete(session.id); }}
                  aria-label={`Delete session: ${session.title}`}
                  title="Delete session"
                >
                  ×
                </button>
              </div>
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

      {/* ── Eval Test Suite ───────────────────────────────────────────── */}
      <div className="sidebar-test-wrap">
        <button
          id="open-test-panel-btn"
          className="sidebar-test-btn"
          onClick={onOpenTestPanel}
          aria-label="Open evaluation test suite"
        >
          <span className="sidebar-test-icon">🧪</span>
          Eval Test Suite
        </button>
      </div>

      {/* ── Footer: Qdrant badge ───────────────────────────────────────── */}
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
