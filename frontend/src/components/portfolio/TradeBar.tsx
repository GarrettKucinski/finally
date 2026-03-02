"use client";

import { useState } from "react";
import { executeTrade } from "@/lib/api";
import { usePortfolioStore } from "@/stores/portfolioStore";
import { formatCurrency } from "@/lib/format";
import { toast } from "sonner";

export function TradeBar() {
  const [ticker, setTicker] = useState("");
  const [quantity, setQuantity] = useState("");
  const [loading, setLoading] = useState(false);

  const handleTrade = async (side: "buy" | "sell") => {
    const trimmedTicker = ticker.trim().toUpperCase();
    if (!trimmedTicker) {
      toast.error("Enter a ticker symbol");
      return;
    }

    const qty = parseFloat(quantity);
    if (isNaN(qty) || qty <= 0) {
      toast.error("Enter a valid quantity");
      return;
    }

    setLoading(true);
    try {
      const result = await executeTrade({
        ticker: trimmedTicker,
        side,
        quantity: qty,
      });
      const verb = side === "buy" ? "Bought" : "Sold";
      toast.success(
        `${verb} ${result.quantity} ${result.ticker} at ${formatCurrency(result.price)}`
      );
      await usePortfolioStore.getState().refresh();
      setTicker("");
      setQuantity("");
    } catch {
      // Error already toasted by apiFetch
    } finally {
      setLoading(false);
    }
  };

  const isDisabled = loading || !ticker.trim() || !quantity.trim();

  return (
    <div className="flex items-center gap-3 rounded-lg border border-border-default bg-surface-secondary p-3">
      <span className="text-xs font-bold uppercase tracking-wider text-text-secondary">
        Trade
      </span>

      <input
        type="text"
        value={ticker}
        onChange={(e) => setTicker(e.target.value.toUpperCase())}
        placeholder="AAPL"
        maxLength={5}
        className="w-20 rounded border border-border-default bg-surface-tertiary px-2 py-1.5 text-sm text-text-primary placeholder:text-text-muted focus:border-primary-blue focus:outline-none"
      />

      <input
        type="number"
        value={quantity}
        onChange={(e) => setQuantity(e.target.value)}
        placeholder="10"
        min="0.0001"
        step="any"
        className="w-24 rounded border border-border-default bg-surface-tertiary px-2 py-1.5 text-sm text-text-primary placeholder:text-text-muted focus:border-primary-blue focus:outline-none"
      />

      <button
        onClick={() => handleTrade("buy")}
        disabled={isDisabled}
        className="rounded bg-price-up px-4 py-1.5 text-sm font-bold text-surface-primary hover:bg-price-up/80 disabled:opacity-50"
      >
        Buy
      </button>

      <button
        onClick={() => handleTrade("sell")}
        disabled={isDisabled}
        className="rounded bg-price-down px-4 py-1.5 text-sm font-bold text-surface-primary hover:bg-price-down/80 disabled:opacity-50"
      >
        Sell
      </button>
    </div>
  );
}
