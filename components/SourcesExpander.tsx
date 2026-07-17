// ─────────────────────────────────────────────────────────────────────────────
// components/SourcesExpander.tsx
// Collapsible "Grounded Sources (Qdrant Chunks)" block shown below
// every assistant message that carries a `source` array.
// ─────────────────────────────────────────────────────────────────────────────

"use client";

import { useState } from "react";

interface SourcesExpanderProps {
  /** Array of citation strings, e.g. "Page 3: Paragraph 2 — ..." */
  sources: string[];
}

export default function SourcesExpander({ sources }: SourcesExpanderProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="src-expander">
      {/* ── Trigger button ──────────────────────────────────────────────── */}
      <button
        id={`src-toggle-${sources[0]?.slice(0, 10)}`}
        className="src-trigger"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
      >
        <span className="src-trigger-left">
          {/* Qdrant blue diamond icon */}
          <span className="src-qdrant-icon">🔷</span>
          <span className="src-label">Grounded Sources</span>
          <span className="src-sublabel">Qdrant Chunks</span>
        </span>
        <span className="src-trigger-right">
          <span className="src-count-badge">{sources.length} chunks</span>
          <span className={`src-chevron ${open ? "open" : ""}`}>›</span>
        </span>
      </button>

      {/* ── Expanded citations list ─────────────────────────────────────── */}
      {open && (
        <div className="src-list" role="list">
          {sources.map((citation, idx) => (
            <div key={idx} className="src-item" role="listitem">
              <span className="src-index">{idx + 1}</span>
              <p className="src-text">{citation}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
