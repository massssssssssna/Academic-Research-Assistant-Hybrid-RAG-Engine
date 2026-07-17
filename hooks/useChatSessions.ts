// ─────────────────────────────────────────────────────────────────────────────
// hooks/useChatSessions.ts
// Custom React hook that owns ALL session state.
// Pure React useState — no localStorage, no DB.
// On every page refresh, state is reset to a single clean empty session.
// ─────────────────────────────────────────────────────────────────────────────

"use client";

import { useState, useCallback, useEffect } from "react";
import type { ChatSession, Message } from "@/types";
import { generateId } from "@/lib/utils";

/** Creates a single fresh empty session */
function makeEmptySession(title = "New Research Chat"): ChatSession {
  const now = new Date();
  return {
    id: generateId(),
    title,
    messages: [],
    pdfName: undefined,
    createdAt: now,
    updatedAt: now,
  };
}

export function useChatSessions() {
  // Initialize with null to avoid SSR/client mismatch — populated after mount
  const [state, setState] = useState<{
    sessions: ChatSession[];
    activeSessionId: string;
  } | null>(null);

  // Only run on client after hydration to avoid random-ID mismatch
  useEffect(() => {
    const first = makeEmptySession();
    setState({ sessions: [first], activeSessionId: first.id });
  }, []);

  const sessions = state?.sessions ?? [];
  const activeSessionId = state?.activeSessionId ?? "";

  // ── Derived: the active session object ────────────────────────────────────
  const activeSession: ChatSession | null =
    sessions.find((s) => s.id === activeSessionId) ?? null;

  // ── Helpers to update the state immutably ─────────────────────────────────
  const setSessions = useCallback(
    (updater: (prev: ChatSession[]) => ChatSession[]) => {
      setState((prev) => prev ? { ...prev, sessions: updater(prev.sessions) } : prev);
    },
    []
  );

  const setActiveSessionId = useCallback((id: string | null) => {
    setState((prev) => prev ? { ...prev, activeSessionId: id ?? prev.activeSessionId } : prev);
  }, []);

  // ── CREATE: add a new empty session at the TOP, make it active ────────────
  const createSession = useCallback(
    (title = "New Research Chat", pdfName?: string): string => {
      const newSession = makeEmptySession(title);
      if (pdfName) newSession.pdfName = pdfName;
      setState((prev) => ({
        sessions: [newSession, ...(prev?.sessions ?? [])],
        activeSessionId: newSession.id,
      }));
      return newSession.id;
    },
    []
  );

  // ── DELETE: remove session; fallback to next available ───────────────────
  const deleteSession = useCallback((id: string) => {
    setState((prev) => {
      if (!prev) return prev;
      const remaining = prev.sessions.filter((s) => s.id !== id);
      const nextActive =
        prev.activeSessionId === id
          ? (remaining[0]?.id ?? "")
          : prev.activeSessionId;
      return { sessions: remaining, activeSessionId: nextActive };
    });
  }, []);

  // ── UPDATE: patch title / pdfName ─────────────────────────────────────────
  const updateSession = useCallback(
    (id: string, updates: Partial<Pick<ChatSession, "title" | "pdfName">>) => {
      setSessions((prev) =>
        prev.map((s) =>
          s.id === id ? { ...s, ...updates, updatedAt: new Date() } : s
        )
      );
    },
    [setSessions]
  );

  // ── ADD MESSAGE ───────────────────────────────────────────────────────────
  const addMessage = useCallback(
    (sessionId: string, msg: Omit<Message, "id" | "timestamp">): Message => {
      const newMsg: Message = {
        ...msg,
        id: generateId(),
        timestamp: new Date(),
      };
      setSessions((prev) =>
        prev.map((s) =>
          s.id === sessionId
            ? { ...s, messages: [...s.messages, newMsg], updatedAt: new Date() }
            : s
        )
      );
      return newMsg;
    },
    [setSessions]
  );

  // ── CLEAR MESSAGES from a session ─────────────────────────────────────────
  const clearMessages = useCallback(
    (sessionId: string) => {
      setSessions((prev) =>
        prev.map((s) =>
          s.id === sessionId
            ? { ...s, messages: [], updatedAt: new Date() }
            : s
        )
      );
    },
    [setSessions]
  );

  return {
    sessions,
    activeSessionId,
    activeSession,
    setActiveSessionId,
    createSession,
    deleteSession,
    updateSession,
    addMessage,
    clearMessages,
  };
}
