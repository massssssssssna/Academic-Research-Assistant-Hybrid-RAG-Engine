// ─────────────────────────────────────────────────────────────────────────────
// components/MessageBubble.tsx
// Renders a single chat message in one of two layouts:
//   • User   → right-aligned, purple-tinted bubble with border
//   • Assistant → left-aligned, dark bubble with "AI" gradient avatar badge
//               + optional SourcesExpander when message.source is present
// ─────────────────────────────────────────────────────────────────────────────

import type { Message } from "@/types";
import { formatTime, markdownToHtml } from "@/lib/utils";
import SourcesExpander from "./SourcesExpander";

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  // ── User message ───────────────────────────────────────────────────────────
  if (isUser) {
    return (
      <div className="msg-row msg-user">
        <div className="bubble user-bubble">
          <p className="bubble-text">{message.content}</p>
          <time className="bubble-time" dateTime={message.timestamp.toISOString()}>
            {formatTime(message.timestamp)}
          </time>
        </div>
      </div>
    );
  }

  // ── Assistant message ──────────────────────────────────────────────────────
  return (
    <div className="msg-row msg-assistant">
      {/* Gradient "AI" avatar badge */}
      <div className="ai-avatar" aria-label="AI assistant">
        AI
      </div>

      {/* Message content + optional sources expander */}
      <div className="assistant-group">
        <div className="bubble assistant-bubble">
          <p
            className="bubble-text"
            dangerouslySetInnerHTML={{ __html: markdownToHtml(message.content) }}
          />
          <time className="bubble-time" dateTime={message.timestamp.toISOString()}>
            {formatTime(message.timestamp)}
          </time>
        </div>

        {/* RAG Citations: only render when source array is present and non-empty */}
        {message.source && message.source.length > 0 && (
          <SourcesExpander sources={message.source} />
        )}
      </div>
    </div>
  );
}
