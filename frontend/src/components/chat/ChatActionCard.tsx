"use client";

import type { ChatExecutedActions } from "@/types/api";
import { formatCurrency } from "@/lib/format";

interface ChatActionCardProps {
  actions: ChatExecutedActions;
}

export function ChatActionCard({ actions }: ChatActionCardProps) {
  const hasTrades = actions.trades?.length > 0;
  const hasWatchlist = actions.watchlist_changes?.length > 0;
  const hasErrors = actions.errors?.length > 0;

  if (!hasTrades && !hasWatchlist && !hasErrors) {
    return null;
  }

  return (
    <div className="mt-2 space-y-1.5">
      {actions.trades?.map((trade, i) => {
        const isBuy = trade.side.toLowerCase() === "buy";
        return (
          <div
            key={`trade-${i}`}
            className={`flex items-center gap-2 rounded bg-[var(--color-surface-tertiary)] px-3 py-2 text-xs border-l-2 ${
              isBuy
                ? "border-[var(--color-price-up)]"
                : "border-[var(--color-price-down)]"
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
              {trade.quantity} {trade.ticker} @ {formatCurrency(trade.price)}
            </span>
            <span className="ml-auto text-[var(--color-text-secondary)]">
              ({formatCurrency(trade.total)})
            </span>
          </div>
        );
      })}

      {actions.watchlist_changes?.map((change, i) => {
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

      {actions.errors?.map((err, i) => (
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
