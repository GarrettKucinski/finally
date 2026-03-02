"use client";

import { useEffect } from "react";
import { useSSE } from "@/hooks/useSSE";
import { usePortfolioStore } from "@/stores/portfolioStore";
import { Header } from "@/components/layout/Header";
import { WatchlistPanel } from "@/components/watchlist/WatchlistPanel";
import { PositionsTable } from "@/components/portfolio/PositionsTable";
import { TradeBar } from "@/components/portfolio/TradeBar";

export function Dashboard() {
  useSSE();

  const refresh = usePortfolioStore((s) => s.refresh);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div className="flex h-screen flex-col">
      <Header />

      <div className="flex flex-1 overflow-hidden">
        <aside className="w-80 flex-shrink-0 overflow-y-auto border-r border-border-default">
          <WatchlistPanel />
        </aside>

        <main className="flex-1 space-y-4 overflow-y-auto p-4">
          <PositionsTable />
          <TradeBar />

          <div className="flex h-64 items-center justify-center rounded-lg border border-border-default bg-surface-secondary p-4">
            <span className="text-text-muted">
              Chart area -- coming in Phase 5
            </span>
          </div>

          <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-border-default bg-surface-secondary/50 p-4">
            <span className="text-text-muted">
              AI Chat -- coming in Phase 5
            </span>
          </div>
        </main>
      </div>
    </div>
  );
}
