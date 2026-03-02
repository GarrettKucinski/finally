"use client";

import { usePriceStore } from "@/stores/priceStore";
import { usePortfolioStore } from "@/stores/portfolioStore";
import { formatCurrency } from "@/lib/format";

const statusConfig = {
  connected: { color: "bg-price-up", label: "Connected" },
  reconnecting: { color: "bg-accent-yellow", label: "Reconnecting" },
  disconnected: { color: "bg-price-down", label: "Disconnected" },
} as const;

export function Header() {
  const connectionStatus = usePriceStore((s) => s.connectionStatus);
  const prices = usePriceStore((s) => s.prices);
  const cashBalance = usePortfolioStore((s) => s.cashBalance);
  const positions = usePortfolioStore((s) => s.positions);

  const liveTotal =
    cashBalance +
    positions.reduce(
      (sum, p) =>
        sum +
        p.quantity *
          (prices[p.ticker]?.price ?? p.current_price ?? p.avg_cost),
      0
    );

  const { color, label } = statusConfig[connectionStatus];

  return (
    <header className="flex items-center justify-between border-b border-border-default bg-surface-secondary px-4 py-2">
      <div className="flex items-center gap-3">
        <span className="text-lg font-bold text-accent-yellow">FinAlly</span>
      </div>

      <div className="flex flex-col items-center">
        <span className="text-xs text-text-muted">Portfolio Value</span>
        <span className="text-lg font-bold text-text-primary">
          {formatCurrency(liveTotal)}
        </span>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex flex-col items-end">
          <span className="text-xs text-text-muted">Cash</span>
          <span className="text-sm text-text-secondary">
            {formatCurrency(cashBalance)}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <span className={`inline-block h-2 w-2 rounded-full ${color}`} />
          <span className="text-xs text-text-muted">{label}</span>
        </div>
      </div>
    </header>
  );
}
