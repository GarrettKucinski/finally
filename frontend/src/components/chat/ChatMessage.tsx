"use client";

import type { ChatMessage as ChatMessageType } from "@/types/api";
import { ChatActionCard } from "./ChatActionCard";

interface ChatMessageProps {
  message: ChatMessageType;
  messageIndex: number;
}

function hasActions(message: ChatMessageType): boolean {
  if (message.proposed_trades && message.proposed_trades.length > 0) return true;
  if (!message.executed_actions) return false;
  const a = message.executed_actions;
  return (
    (a.watchlist_changes?.length ?? 0) > 0 ||
    (a.errors?.length ?? 0) > 0
  );
}

export function ChatMessage({ message, messageIndex }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={`mb-2 flex flex-col ${isUser ? "items-end" : "items-start"}`}>
      <span className="mb-0.5 text-xs text-[var(--color-text-muted)]">
        {isUser ? "You" : "FinAlly"}
      </span>
      <div
        className={`max-w-[85%] rounded-lg px-3 py-2 text-sm text-[var(--color-text-primary)] ${
          isUser
            ? "bg-[var(--color-accent-purple)]/20"
            : "bg-[var(--color-surface-tertiary)]"
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {!isUser && hasActions(message) && (
          <ChatActionCard
            actions={message.executed_actions}
            proposed_trades={message.proposed_trades}
            messageIndex={messageIndex}
          />
        )}
      </div>
    </div>
  );
}
