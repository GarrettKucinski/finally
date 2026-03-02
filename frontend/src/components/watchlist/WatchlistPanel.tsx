"use client";

import { useEffect, useState, useCallback } from "react";
import { usePriceStore } from "@/stores/priceStore";
import { fetchWatchlist, addTicker, removeTicker } from "@/lib/api";
import { PriceFlash } from "@/components/ui/PriceFlash";
import { Sparkline } from "@/components/watchlist/Sparkline";
import { formatPercent } from "@/lib/format";

const EMPTY_HISTORY: number[] = [];

function WatchlistRow({
  ticker,
  onRemove,
}: {
  ticker: string;
  onRemove: (ticker: string) => void;
}) {
  const priceData = usePriceStore((s) => s.prices[ticker]);
  const history = usePriceStore((s) => s.priceHistory[ticker] ?? EMPTY_HISTORY);

  return (
    <div className="group flex items-center gap-2 border-b border-border-default px-3 py-2 hover:bg-surface-tertiary">
      <span className="w-14 flex-shrink-0 font-medium text-text-primary">
        {ticker}
      </span>

      <div className="flex-1 text-right">
        {priceData ? (
          <PriceFlash price={priceData.price} direction={priceData.direction} />
        ) : (
          <span className="text-text-muted">---</span>
        )}
      </div>

      <div className="w-18 text-right text-sm">
        {priceData ? (
          <span
            className={
              priceData.change_percent > 0
                ? "text-price-up"
                : priceData.change_percent < 0
                  ? "text-price-down"
                  : "text-text-muted"
            }
          >
            {formatPercent(priceData.change_percent)}
          </span>
        ) : (
          <span className="text-text-muted">---</span>
        )}
      </div>

      <div className="w-16 flex-shrink-0 flex items-center justify-center">
        <Sparkline data={history} width={60} height={20} />
      </div>

      <button
        onClick={() => onRemove(ticker)}
        className="ml-1 opacity-0 transition-opacity group-hover:opacity-100 text-text-muted hover:text-price-down"
        title={`Remove ${ticker}`}
      >
        x
      </button>
    </div>
  );
}

export function WatchlistPanel() {
  const [tickers, setTickers] = useState<string[]>([]);
  const [newTicker, setNewTicker] = useState("");
  const [loading, setLoading] = useState(false);

  const loadWatchlist = useCallback(async () => {
    try {
      const items = await fetchWatchlist();
      setTickers(items.map((item) => item.ticker));
    } catch {
      // Error already toasted by apiFetch
    }
  }, []);

  useEffect(() => {
    loadWatchlist();
  }, [loadWatchlist]);

  const handleAdd = async () => {
    const ticker = newTicker.trim().toUpperCase();
    if (!ticker) return;
    setLoading(true);
    try {
      await addTicker(ticker);
      setNewTicker("");
      await loadWatchlist();
    } catch {
      // Error already toasted
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = async (ticker: string) => {
    try {
      await removeTicker(ticker);
      await loadWatchlist();
    } catch {
      // Error already toasted
    }
  };

  return (
    <div className="flex h-full flex-col bg-surface-secondary">
      <div className="border-b border-border-default px-3 py-2">
        <h2 className="text-sm font-bold uppercase tracking-wider text-text-secondary">
          Watchlist
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto">
        {tickers.map((ticker) => (
          <WatchlistRow key={ticker} ticker={ticker} onRemove={handleRemove} />
        ))}
        {tickers.length === 0 && (
          <div className="px-3 py-4 text-center text-sm text-text-muted">
            No tickers in watchlist.
          </div>
        )}
      </div>

      <div className="border-t border-border-default p-2">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleAdd();
          }}
          className="flex gap-2"
        >
          <input
            type="text"
            value={newTicker}
            onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
            placeholder="TICKER"
            maxLength={5}
            className="flex-1 rounded border border-border-default bg-surface-tertiary px-2 py-1 text-sm text-text-primary placeholder:text-text-muted focus:border-primary-blue focus:outline-none"
          />
          <button
            type="submit"
            disabled={loading || !newTicker.trim()}
            className="rounded bg-primary-blue px-3 py-1 text-sm font-bold text-surface-primary hover:bg-primary-blue/80 disabled:opacity-50"
          >
            Add
          </button>
        </form>
      </div>
    </div>
  );
}
