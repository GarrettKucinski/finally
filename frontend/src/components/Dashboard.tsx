"use client";

import { useEffect, useState, useMemo } from "react";
import { useSSE } from "@/hooks/useSSE";
import { usePortfolioStore } from "@/stores/portfolioStore";
import { usePriceStore } from "@/stores/priceStore";
import type { ChartDataPoint } from "@/stores/priceStore";
import { fetchPortfolioHistory } from "@/lib/api";
import type { SnapshotPoint } from "@/types/api";
import { Header } from "@/components/layout/Header";
import { WatchlistPanel } from "@/components/watchlist/WatchlistPanel";
import { PositionsTable } from "@/components/portfolio/PositionsTable";
import { TradeBar } from "@/components/portfolio/TradeBar";
import TickerChart from "@/components/chart/TickerChart";
import PortfolioHeatmap from "@/components/portfolio/PortfolioHeatmap";
import type { HeatmapPosition } from "@/components/portfolio/PortfolioHeatmap";
import PnLChart from "@/components/portfolio/PnLChart";
import { ChatPanel } from "@/components/chat/ChatPanel";

const EMPTY_CHART: ChartDataPoint[] = [];

export function Dashboard() {
  useSSE();

  const refresh = usePortfolioStore((s) => s.refresh);
  const positions = usePortfolioStore((s) => s.positions);
  const positionsLength = usePortfolioStore((s) => s.positions.length);
  const prices = usePriceStore((s) => s.prices);
  const chartHistory = usePriceStore((s) => s.chartHistory);

  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [chatOpen, setChatOpen] = useState(true);
  const [pnlData, setPnlData] = useState<SnapshotPoint[]>([]);

  // Load portfolio on mount
  useEffect(() => {
    refresh();
  }, [refresh]);

  // Fetch portfolio history on mount and when positions change (trade happened)
  useEffect(() => {
    fetchPortfolioHistory()
      .then(setPnlData)
      .catch(() => {});
  }, [positionsLength]);

  // Chart data for selected ticker
  const chartData = useMemo(() => {
    if (!selectedTicker) return EMPTY_CHART;
    return chartHistory[selectedTicker] ?? EMPTY_CHART;
  }, [selectedTicker, chartHistory]);

  // Transform positions to heatmap format
  const heatmapData: HeatmapPosition[] = useMemo(() => {
    return positions
      .filter((p) => p.quantity > 0)
      .map((p) => {
        const currentPrice =
          prices[p.ticker]?.price ?? p.current_price ?? p.avg_cost;
        return {
          name: p.ticker,
          size: Math.abs(currentPrice * p.quantity),
          pnlPercent:
            p.avg_cost !== 0
              ? ((currentPrice - p.avg_cost) / p.avg_cost) * 100
              : 0,
        };
      });
  }, [positions, prices]);

  return (
    <div className="flex h-screen flex-col">
      <Header />

      <div className="flex flex-1 overflow-hidden">
        {/* Left: Watchlist */}
        <aside className="w-80 flex-shrink-0 overflow-y-auto border-r border-border-default">
          <WatchlistPanel
            selectedTicker={selectedTicker ?? undefined}
            onSelectTicker={setSelectedTicker}
          />
        </aside>

        {/* Center: Main content */}
        <main className="flex-1 space-y-4 overflow-y-auto p-4">
          {/* Ticker Chart */}
          {selectedTicker ? (
            <TickerChart ticker={selectedTicker} data={chartData} />
          ) : (
            <div className="flex h-64 items-center justify-center rounded-lg border border-border-default bg-surface-secondary p-4">
              <span className="text-text-muted">
                Select a ticker from the watchlist to view its chart
              </span>
            </div>
          )}

          {/* Portfolio visualizations: Heatmap + P&L Chart side by side */}
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-lg border border-border-default bg-surface-secondary p-4">
              <h3 className="mb-2 text-sm font-bold uppercase tracking-wider text-text-secondary">
                Portfolio Heatmap
              </h3>
              <PortfolioHeatmap positions={heatmapData} />
            </div>
            <div className="rounded-lg border border-border-default bg-surface-secondary p-4">
              <h3 className="mb-2 text-sm font-bold uppercase tracking-wider text-text-secondary">
                Portfolio Value
              </h3>
              <PnLChart data={pnlData} />
            </div>
          </div>

          {/* Positions + Trade Bar */}
          <PositionsTable />
          <TradeBar />
        </main>

        {/* Right: Chat sidebar */}
        <aside
          className={`${chatOpen ? "w-96" : "w-0"} flex-shrink-0 overflow-hidden border-l border-border-default transition-all duration-300`}
        >
          <ChatPanel open={chatOpen} onToggle={() => setChatOpen(!chatOpen)} />
        </aside>
      </div>

      {/* Floating chat toggle when sidebar is collapsed */}
      {!chatOpen && (
        <button
          onClick={() => setChatOpen(true)}
          className="fixed bottom-6 right-6 z-10 flex h-14 w-14 items-center justify-center rounded-full bg-accent-purple text-white shadow-lg shadow-accent-purple/30 transition-transform hover:scale-110 hover:shadow-accent-purple/50 active:scale-95"
          aria-label="AI"
          title="Open AI Chat"
        >
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
            <path
              d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5Z"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="currentColor"
              fillOpacity="0.15"
            />
          </svg>
        </button>
      )}
    </div>
  );
}
