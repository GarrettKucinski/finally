"use client";

import { useState, useRef, useEffect } from "react";
import { useChatStore } from "@/stores/chatStore";
import { ChatMessage } from "./ChatMessage";

interface ChatPanelProps {
  open: boolean;
  onToggle: () => void;
}

export function ChatPanel({ open, onToggle }: ChatPanelProps) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const messages = useChatStore((s) => s.messages);
  const loading = useChatStore((s) => s.loading);
  const send = useChatStore((s) => s.send);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading) return;
    setInput("");
    send(trimmed);
  };

  return (
    <div className="flex h-full flex-col border-l border-[var(--color-border-default)] bg-[var(--color-surface-secondary)]">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--color-border-default)] px-4 py-3">
        <h2 className="text-sm font-bold text-[var(--color-text-primary)]">
          AI Assistant
        </h2>
        <button
          onClick={onToggle}
          className="text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors"
          aria-label={open ? "Collapse chat" : "Expand chat"}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            className={`transition-transform ${open ? "" : "rotate-180"}`}
          >
            <path
              d="M10 12L6 8L10 4"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-center text-sm text-[var(--color-text-muted)] max-w-[220px]">
              Ask FinAlly about your portfolio, request trades, or get market
              analysis.
            </p>
          </div>
        ) : (
          <>
            {messages.map((msg, i) => (
              <ChatMessage key={i} message={msg} messageIndex={i} />
            ))}
            {loading && (
              <div className="mb-2 flex items-start">
                <div className="flex items-center gap-1 rounded-lg bg-[var(--color-surface-tertiary)] px-3 py-2">
                  <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--color-text-muted)]" />
                  <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--color-text-muted)] [animation-delay:150ms]" />
                  <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--color-text-muted)] [animation-delay:300ms]" />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </>
        )}
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-2 border-t border-[var(--color-border-default)] px-4 py-3"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask FinAlly..."
          className="flex-1 rounded border border-[var(--color-border-default)] bg-[var(--color-surface-tertiary)] px-3 py-1.5 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] outline-none focus:border-[var(--color-primary-blue)]"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="rounded bg-[var(--color-accent-purple)] px-3 py-1.5 text-sm font-bold text-white disabled:opacity-40 hover:opacity-90 transition-opacity"
        >
          Send
        </button>
      </form>
    </div>
  );
}
