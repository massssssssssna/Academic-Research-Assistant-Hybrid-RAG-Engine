// ─────────────────────────────────────────────────────────────────────────────
// lib/utils.ts
// Pure utility helpers — no React imports, no side effects.
// Imported by components, hooks, and the mock-data file.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Generate a stable unique ID using crypto.randomUUID.
 * Falls back to timestamp+random for older environments.
 * NOTE: This is only called inside useState initializers which run
 * client-side only — ensuring no SSR/client hydration mismatch.
 */
export function generateId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Format a Date to a 12-hour "HH:MM AM/PM" time string.
 * Shown as the timestamp under each message bubble.
 */
export function formatTime(date: Date): string {
  return new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  }).format(date);
}

/**
 * Format a Date to a human-friendly relative label for the sidebar.
 * Examples: "Just now", "3h ago", "Yesterday", "Jul 12"
 */
export function formatDate(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const hours = Math.floor(diffMs / (1000 * 60 * 60));
  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (hours < 1)  return "Just now";
  if (hours < 24) return `${hours}h ago`;
  if (days === 1) return "Yesterday";
  if (days < 7)   return `${days}d ago`;
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(date);
}

/**
 * Truncate text to `max` characters, appending an ellipsis if trimmed.
 * Used in the sidebar session titles and PDF badge labels.
 */
export function truncate(text: string, max: number): string {
  return text.length > max ? text.slice(0, max) + "…" : text;
}

/**
 * Convert a tiny subset of Markdown to safe HTML for rendering in message bubbles.
 * Supports: **bold** → <strong>, newlines → <br />.
 * Kept intentionally minimal — no external lib needed.
 */
export function markdownToHtml(text: string): string {
  // Escape HTML entities to prevent React rendering crashes from raw HTML injection
  const escaped = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");

  // Basic markdown parsing
  return escaped
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br />");
}
