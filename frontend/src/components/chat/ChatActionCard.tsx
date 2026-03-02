"use client";

import type { ChatExecutedActions, ProposedTrade } from "@/types/api";
import { formatCurrency } from "@/lib/format";
import { useChatStore } from "@/stores/chatStore";

interface ChatActionCardProps {
  actions?: ChatExecutedActions;
  proposed_trades?: ProposedTrade[];
  messageIndex: number;
}

export function ChatActionCard({
  actions,
  proposed_trades,
  messageIndex,
}: ChatActionCardProps) {
  const confirmTrade = useChatStore((s) => s.confirmTrade);
  const dismissTrade = useChatStore((s) => s.dismissTrade);

  const hasWatchlist = (actions?.watchlist_changes?.length ?? 0) > 0;
  const hasErrors = (actions?.errors?.length ?? 0) > 0;
  const hasProposed = (proposed_trades?.length ?? 0) > 0;

  if (!hasWatchlist && !hasErrors && !hasProposed) {
    return null;
  }

  return (
    <div className="mt-2 space-y-1.5">
      {proposed_trades?.map((trade, i) => (
        <ProposedTradeCard
          key={`proposed-${i}`}
          trade={trade}
          onConfirm={() => confirmTrade(messageIndex, i)}
          onDismiss={() => dismissTrade(messageIndex, i)}
        />
      ))}

      {actions?.watchlist_changes?.map((change, i) => {
        const isAdd = change.action.toLowerCase() === "add";
        return (
          <div
            key={`wl-${i}`}
            className={`flex items-center gap-2 rounded bg-[var(--color-surface-tertiary)] px-3 py-2 text-xs border-l-2 ${
              isAdd
                ? "border-[var(--color-price-up)]"
                : "border-[var(--color-price-down)]"
            }`}
          >
            <span
              className={`font-bold ${
                isAdd
                  ? "text-[var(--color-price-up)]"
                  : "text-[var(--color-price-down)]"
              }`}
            >
              {isAdd ? "+" : "-"}
            </span>
            <span className="text-[var(--color-text-primary)]">
              {isAdd ? "Added" : "Removed"} {change.ticker}{" "}
              {isAdd ? "to" : "from"} watchlist
            </span>
          </div>
        );
      })}

      {actions?.errors?.map((err, i) => (
        <div
          key={`err-${i}`}
          className="flex items-center gap-2 rounded bg-[var(--color-surface-tertiary)] px-3 py-2 text-xs border-l-2 border-[var(--color-accent-yellow)]"
        >
          <span className="text-[var(--color-accent-yellow)]">!</span>
          <span className="text-[var(--color-accent-yellow)]">
            {err.ticker}: {err.detail}
          </span>
        </div>
      ))}
    </div>
  );
}

function ProposedTradeCard({
  trade,
  onConfirm,
  onDismiss,
}: {
  trade: ProposedTrade;
  onConfirm: () => void;
  onDismiss: () => void;
}) {
  const isBuy = trade.side.toLowerCase() === "buy";

  if (trade.status === "confirmed" && trade.result) {
    return (
      <div className="flex items-center gap-2 rounded bg-[var(--color-surface-tertiary)] px-3 py-2 text-xs border-l-2 border-[var(--color-price-up)]">
        <span className="font-bold uppercase text-[var(--color-price-up)]">
          {trade.side}
        </span>
        <span className="text-[var(--color-text-primary)]">
          {trade.result.quantity} {trade.result.ticker} @{" "}
          {formatCurrency(trade.result.price)}
        </span>
        <span className="ml-auto text-[var(--color-text-secondary)]">
          ({formatCurrency(trade.result.total)})
        </span>
        <span className="text-[var(--color-price-up)] font-medium">
          Confirmed
        </span>
      </div>
    );
  }

  if (trade.status === "dismissed") {
    return (
      <div className="flex items-center gap-2 rounded bg-[var(--color-surface-tertiary)] px-3 py-2 text-xs border-l-2 border-[var(--color-text-muted)] opacity-50">
        <span className="font-bold uppercase text-[var(--color-text-muted)]">
          {trade.side}
        </span>
        <span className="text-[var(--color-text-muted)]">
          {trade.quantity} {trade.ticker}
        </span>
        <span className="ml-auto text-[var(--color-text-muted)] font-medium">
          Dismissed
        </span>
      </div>
    );
  }

  if (trade.status === "failed") {
    return (
      <div className="flex items-center gap-2 rounded bg-[var(--color-surface-tertiary)] px-3 py-2 text-xs border-l-2 border-[var(--color-price-down)]">
        <span className="font-bold uppercase text-[var(--color-price-down)]">
          {trade.side}
        </span>
        <span className="text-[var(--color-text-primary)]">
          {trade.quantity} {trade.ticker}
        </span>
        <span className="ml-auto text-[var(--color-price-down)]">
          {trade.error ?? "Trade failed"}
        </span>
      </div>
    );
  }

  // pending
  return (
    <div
      className={`flex items-center gap-2 rounded bg-[var(--color-surface-tertiary)] px-3 py-2 text-xs border-l-2 ${
        isBuy
          ? "border-[var(--color-accent-yellow)]"
          : "border-[var(--color-accent-yellow)]"
      }`}
    >
      <span
        className={`font-bold uppercase ${
          isBuy
            ? "text-[var(--color-price-up)]"
            : "text-[var(--color-price-down)]"
        }`}
      >
        {trade.side}
      </span>
      <span className="text-[var(--color-text-primary)]">
        {trade.quantity} {trade.ticker}
      </span>
      <div className="ml-auto flex items-center gap-1.5">
        <button
          onClick={onConfirm}
          className="rounded bg-[var(--color-price-up)]/20 px-2 py-0.5 text-[var(--color-price-up)] font-bold hover:bg-[var(--color-price-up)]/30 transition-colors"
        >
          Confirm
        </button>
        <button
          onClick={onDismiss}
          className="rounded bg-[var(--color-text-muted)]/20 px-2 py-0.5 text-[var(--color-text-muted)] font-bold hover:bg-[var(--color-text-muted)]/30 transition-colors"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}
