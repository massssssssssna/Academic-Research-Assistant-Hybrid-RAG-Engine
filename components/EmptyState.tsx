// ─────────────────────────────────────────────────────────────────────────────
// components/EmptyState.tsx
// Shown in the center workspace when the active session has no PDF yet.
// Two internal states controlled by the `isIndexing` prop:
//   • false → drag-and-drop PDF dropzone + feature grid
//   • true  → animated indexing spinner with progress bar
// ─────────────────────────────────────────────────────────────────────────────

"use client";

interface EmptyStateProps {
  /** Called when a valid .pdf File is chosen by the user */
  onFileSelect: (file: File) => void;
  /** When true, shows the indexing animation instead of the dropzone */
  isIndexing: boolean;
}

export default function EmptyState({ isIndexing }: EmptyStateProps) {
  // ── Indexing animation view ─────────────────────────────────────────────
  if (isIndexing) {
    return (
      <div className="empty-state">
        <div className="indexing-card">
          <div className="indexing-spinner-ring" aria-hidden="true">
            <div className="indexing-spinner-inner" />
          </div>
          <h3 className="indexing-title">Indexing into Qdrant Cloud…</h3>
          <p className="indexing-sub">
            Chunking, embedding, and uploading your document or ZIP data to the vector database.
          </p>
          <div className="indexing-progress-track">
            <div className="indexing-progress-fill" />
          </div>
          <p className="indexing-steps">
            ✓ Files parsed &nbsp;·&nbsp; ✓ Chunks created &nbsp;·&nbsp; ⟳ Embedding…
          </p>
        </div>
      </div>
    );
  }

  // ── Dropzone view ───────────────────────────────────────────────────────
  return (
    <div className="empty-state">
      {/* Glowing sparkle heading */}
      <div className="empty-sparkle" aria-hidden="true">✨</div>
      <h2 className="empty-title">Start Your Academic RAG Query</h2>
      <p className="empty-desc">
        Upload a research paper (PDF) or data package (ZIP) to begin. Every AI answer will be grounded in
        your document using <strong>Qdrant</strong> vector search with chunk-level citations.
      </p>

      {/* ── Drag-and-drop dropzone (Temporarily Removed) ───────────────── */}
      {/* 
        The upload dropzone was here. Removed per user request.
        Upload can still be done from the sidebar button.
      */}

      {/* ── Feature pills ─────────────────────────────────────────────── */}
      <div className="empty-features">
        {[
          { icon: "🧠", label: "Vector Search",   desc: "Qdrant-powered retrieval"  },
          { icon: "📌", label: "Cited Answers",   desc: "Chunk-level citations"        },
          { icon: "💬", label: "Multi-session",   desc: "Manage all your research"     },
          { icon: "⚡", label: "Fast Indexing",   desc: "< 3 seconds per document"     },
        ].map(({ icon, label, desc }) => (
          <div key={label} className="feature-pill">
            <span className="feature-pill-icon">{icon}</span>
            <div>
              <strong>{label}</strong>
              <p>{desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
