"use client";

import { usePriceStore } from "@/stores/priceStore";
import { usePortfolioStore } from "@/stores/portfolioStore";
import { PriceFlash } from "@/components/ui/PriceFlash";
import { formatCurrency, formatPercent, formatQuantity } from "@/lib/format";

export function PositionsTable() {
  const positions = usePortfolioStore((s) => s.positions);
  const prices = usePriceStore((s) => s.prices);

  if (positions.length === 0) {
    return (
      <div className="rounded-lg border border-border-default bg-surface-secondary p-4">
        <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-text-secondary">
          Positions
        </h2>
        <p className="text-sm text-text-muted">
          No positions yet. Use the trade bar to buy shares.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-border-default bg-surface-secondary">
      <div className="px-3 py-2">
        <h2 className="text-sm font-bold uppercase tracking-wider text-text-secondary">
          Positions
        </h2>
      </div>
      <table className="w-full">
        <thead>
          <tr className="bg-surface-tertiary text-xs uppercase tracking-wider text-text-secondary">
            <th className="px-3 py-2 text-left">Ticker</th>
            <th className="px-3 py-2 text-right">Qty</th>
            <th className="px-3 py-2 text-right">Avg Cost</th>
            <th className="px-3 py-2 text-right">Price</th>
            <th className="px-3 py-2 text-right">P&L</th>
            <th className="px-3 py-2 text-right">% Change</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((p) => {
            const live = prices[p.ticker];
            const currentPrice =
              live?.price ?? p.current_price ?? p.avg_cost;
            const direction = live?.direction ?? "flat";
            const pnl = (currentPrice - p.avg_cost) * p.quantity;
            const pnlPct =
              p.avg_cost !== 0
                ? ((currentPrice - p.avg_cost) / p.avg_cost) * 100
                : 0;
            const pnlColor =
              pnl > 0
                ? "text-price-up"
                : pnl < 0
                  ? "text-price-down"
                  : "text-text-muted";

            return (
              <tr
                key={p.ticker}
                className="border-t border-border-default hover:bg-surface-tertiary/50"
              >
                <td className="px-3 py-2 text-sm font-medium text-text-primary">
                  {p.ticker}
                </td>
                <td className="px-3 py-2 text-right text-sm text-text-secondary">
                  {formatQuantity(p.quantity)}
                </td>
                <td className="px-3 py-2 text-right text-sm text-text-secondary">
                  {formatCurrency(p.avg_cost)}
                </td>
                <td className="px-3 py-2 text-right text-sm">
                  <PriceFlash price={currentPrice} direction={direction} />
                </td>
                <td className={`px-3 py-2 text-right text-sm ${pnlColor}`}>
                  {formatCurrency(pnl)}
                </td>
                <td className={`px-3 py-2 text-right text-sm ${pnlColor}`}>
                  {formatPercent(pnlPct)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
