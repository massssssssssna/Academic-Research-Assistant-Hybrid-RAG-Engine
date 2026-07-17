// ─────────────────────────────────────────────────────────────────────────────
// lib/mockData.ts  — RETIRED
// Mock sessions are no longer used. The app starts with a single clean session
// managed entirely in React state. This file is kept to avoid import errors.
// ─────────────────────────────────────────────────────────────────────────────

import type { ChatSession } from "@/types";

/** @deprecated — no longer called. Use useChatSessions hook instead. */
export function createMockSessions(): ChatSession[] {
  return [];
}
