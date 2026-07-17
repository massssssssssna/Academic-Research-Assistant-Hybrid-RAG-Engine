// ─────────────────────────────────────────────────────────────────────────────
// components/LoadingBubble.tsx
// Animated "thinking" indicator displayed while:
//   • A message is being processed (text: "Searching Qdrant & Synthesizing...")
//   • A PDF is being indexed     (text: "Indexing into Qdrant Cloud...")
// Matches the assistant bubble layout so it feels like a live message.
// ─────────────────────────────────────────────────────────────────────────────

interface LoadingBubbleProps {
  text?: string;
}

export default function LoadingBubble({
  text = "Searching Qdrant & Synthesizing response…",
}: LoadingBubbleProps) {
  return (
    <div className="msg-row msg-assistant loading-msg-row">
      <div className="ai-avatar" aria-label="AI assistant">
        AI
      </div>
      <div className="assistant-group">
        <div className="bubble assistant-bubble loading-bubble">
          {/* Three bouncing dots */}
          <div className="loading-dots" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
          <p className="loading-label">{text}</p>
        </div>
      </div>
    </div>
  );
}
