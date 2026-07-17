// ─────────────────────────────────────────────────────────────────────────────
// components/Header.tsx
// Top bar of the center workspace.
// Shows: active session title · PDF filename badge · Upload PDF button · Clear
// ─────────────────────────────────────────────────────────────────────────────

"use client";

import { useRef } from "react";
import type { ChatSession } from "@/types";

interface HeaderProps {
  session: ChatSession | null;
  onClearChat: () => void;
  onFileSelect: (file: File) => void;
}

export default function Header({ session, onClearChat, onFileSelect }: HeaderProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onFileSelect(file);
      // Reset so the same file can be uploaded again
      e.target.value = "";
    }
  };

  return (
    <header className="app-header" role="banner">
      {/* ── Left: session title + PDF badge ──────────────────────────────── */}
      <div className="header-left">
        {session ? (
          <>
            <span className="header-session-dot" aria-hidden="true">💬</span>
            <h1 className="header-session-title">
              {session.title}
            </h1>
            {/* PDF badge — visible only when a document is indexed */}
            {session.pdfName && (
              <span className="header-pdf-badge" title={session.pdfName}>
                📄 {session.pdfName}
              </span>
            )}
          </>
        ) : (
          <h1 className="header-session-title">Academic &amp; Research Assistant</h1>
        )}
      </div>

      {/* ── Right: controls ───────────────────────────────────────────────── */}
      <div className="header-right">
        {/* Qdrant live indicator */}
        <div className="header-qdrant-status" aria-label="Qdrant connected">
          <span className="header-status-dot"></span>
          <span className="header-status-label">Qdrant</span>
        </div>

        {/* Hidden file input — triggered by the Upload PDF button */}
        <input
          ref={fileInputRef}
          id="header-pdf-input"
          type="file"
          accept=".pdf,.zip"
          hidden
          onChange={handleInputChange}
        />

        {/* Upload PDF button (always visible) */}
        <button
          id="header-upload-btn"
          className="header-upload-btn"
          onClick={() => fileInputRef.current?.click()}
          aria-label="Upload a document or ZIP package"
          title="Upload PDF/ZIP Document"
        >
          <span aria-hidden="true">📤</span>
          <span>Upload File</span>
        </button>

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
