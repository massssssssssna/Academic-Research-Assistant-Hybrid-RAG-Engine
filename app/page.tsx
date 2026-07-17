// ─────────────────────────────────────────────────────────────────────────────
// app/page.tsx
// Root page — single source of truth for all UI state.
// Sessions live in React state only (no localStorage, no DB).
// Refreshing the browser starts completely fresh.
// ─────────────────────────────────────────────────────────────────────────────

"use client";

import { useState, useCallback } from "react";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import ChatArea from "@/components/ChatArea";
import { useChatSessions } from "@/hooks/useChatSessions";

const BACKEND_URL = "";

const OFFLINE_MSG =
  "⚠️ **Backend server is not responding.** Please run the following command in your terminal:\n```\n.venv\\Scripts\\uvicorn main:app --reload --port 8000\n```";

export default function HomePage() {
  // ── Session management ────────────────────────────────────────────────
  const {
    sessions,
    activeSessionId,
    activeSession,
    setActiveSessionId,
    createSession,
    deleteSession,
    updateSession,
    addMessage,
    clearMessages,
  } = useChatSessions();

  // ── Local UI state ────────────────────────────────────────────────────
  const [inputValue, setInputValue] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isIndexing, setIsIndexing] = useState<boolean>(false);

  // ── RAG Hyperparameters ───────────────────────────────────────────────
  const CHUNK_SIZE = 700;
  const CHUNK_OVERLAP = 120;
  const TOP_K = 7;

  // ── Helper: safe JSON fetch with backend-offline detection ────────────
  const safeFetch = async (url: string, options: RequestInit) => {
    try {
      const res = await fetch(url, options);
      if (!res.ok) {
        const errorText = await res.text().catch(() => "");
        console.error(`API Error (${res.status}): ${res.statusText} - ${errorText}`);
        throw new Error(`API Error (${res.status}): ${errorText || res.statusText}`);
      }
      return res;
    } catch (err: any) {
      console.error("Fetch failed:", err);
      throw err;
    }
  };

  // ── Initialize / Re-Index Handler (sidebar button) ───────────────────
  const handleReindex = useCallback(async () => {
    // Ensure there's an active session to post the status message into
    const sessionId = activeSessionId ?? createSession();
    setIsIndexing(true);

    const res = await safeFetch(`${BACKEND_URL}/api/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chunk_size: CHUNK_SIZE,
        chunk_overlap: CHUNK_OVERLAP,
      }),
    });

    setIsIndexing(false);

    if (!res) {
      addMessage(sessionId, { role: "assistant", content: OFFLINE_MSG });
      return;
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      addMessage(sessionId, {
        role: "assistant",
        content: `❌ **Ingestion failed:** ${err?.detail ?? res.statusText}`,
      });
      return;
    }

    const data = await res.json();
    addMessage(sessionId, {
      role: "assistant",
      content: `✅ **Indexing complete!** ${data.total_chunks} chunks stored in Qdrant.`,
    });
  }, [activeSessionId, createSession, addMessage]);

  // ── PDF / File Select Handler (dropzone & header button) ─────────────
  const handleFileSelect = useCallback(
    async (file: File) => {
      const filename = file.name;

      // Attach file to active session, or create new one
      let sessionId = activeSessionId;
      if (!sessionId) {
        sessionId = createSession(filename, filename);
      } else {
        updateSession(sessionId, { title: filename, pdfName: filename });
      }

      setIsIndexing(true);
      // Small delay so the UI shows the indexing spinner
      await new Promise((r) => setTimeout(r, 400));

      const formData = new FormData();
      formData.append("file", file);

      let res;
      try {
        res = await safeFetch(`${BACKEND_URL}/api/upload`, {
          method: "POST",
          body: formData,
        });
      } catch (err: any) {
        setIsIndexing(false);
        addMessage(sessionId, { role: "assistant", content: `⚠️ **Upload Failed:** ${err.message}` });
        return;
      }

      setIsIndexing(false);

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        addMessage(sessionId, {
          role: "assistant",
          content: `❌ **Ingestion failed for \`${filename}\`:** ${err?.detail ?? res.statusText}`,
        });
        return;
      }

      const data = await res.json();
      addMessage(sessionId, {
        role: "assistant",
        content: `✅ **\`${filename}\`** indexed into Qdrant (${data.total_chunks} chunks). Ask me anything about this document!`,
      });
    },
    [activeSessionId, createSession, updateSession, addMessage]
  );

  // ── Send Message Handler ──────────────────────────────────────────────
  const handleSend = useCallback(async () => {
    const query = inputValue.trim();
    if (!query || isLoading || isIndexing) return;

    // Ensure a session exists
    const sessionId = activeSessionId ?? createSession();

    addMessage(sessionId, { role: "user", content: query });
    setInputValue("");
    setIsLoading(true);

    // Map existing messages to a simple format for the backend
    const chat_history = activeSession?.messages.map(m => ({
      role: m.role,
      content: m.content
    })) || [];

    let res;
    try {
      res = await safeFetch(`${BACKEND_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, top_k: TOP_K, chat_history }),
      });
    } catch (err: any) {
      setIsLoading(false);
      addMessage(sessionId, { role: "assistant", content: `⚠️ **Chat Failed:** ${err.message}` });
      return;
    }

    setIsLoading(false);

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      addMessage(sessionId, {
        role: "assistant",
        content: `❌ **Query failed:** ${err?.detail ?? res.statusText}`,
      });
      return;
    }

    const data = await res.json();
    addMessage(sessionId, {
      role: "assistant",
      content: data.answer,
      source: data.sources,
    });
  }, [
    inputValue,
    activeSessionId,
    activeSession,
    createSession,
    addMessage,
    isLoading,
    isIndexing,
  ]);

  // ── New Session Handler ───────────────────────────────────────────────
  const handleNewSession = useCallback(() => {
    createSession("New Research Chat");
    setInputValue("");
  }, [createSession]);

  // ── Clear Chat Handler ────────────────────────────────────────────────
  const handleClearChat = useCallback(() => {
    if (activeSessionId) clearMessages(activeSessionId);
  }, [activeSessionId, clearMessages]);

  // ── Render ─────────────────────────────────────────────────────────────
  return (
    <div className="app-root">
      {/* Left sidebar */}
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelect={setActiveSessionId}
        onNew={handleNewSession}
        onDelete={deleteSession}
        onReindex={handleReindex}
        isIndexing={isIndexing}
      />

      {/* Center workspace */}
      <div className="workspace">
        <Header
          session={activeSession}
          onClearChat={handleClearChat}
          onFileSelect={handleFileSelect}
        />

        <ChatArea
          session={activeSession}
          inputValue={inputValue}
          onInputChange={setInputValue}
          onSend={handleSend}
          onFileSelect={handleFileSelect}
          isLoading={isLoading}
          isIndexing={isIndexing}
          topK={TOP_K}
        />
      </div>
    </div>
  );
}
