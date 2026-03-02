import { create } from "zustand";
import type { PriceUpdate } from "@/types/api";

export type ConnectionStatus = "connected" | "reconnecting" | "disconnected";

export interface ChartDataPoint {
  time: number; // Unix timestamp in seconds (Lightweight Charts format)
  value: number; // price
}

const MAX_HISTORY_POINTS = 50;

interface PriceStore {
  prices: Record<string, PriceUpdate>;
  priceHistory: Record<string, number[]>; // for Sparkline
  chartHistory: Record<string, ChartDataPoint[]>; // for TickerChart
  connectionStatus: ConnectionStatus;
  updatePrices: (data: Record<string, PriceUpdate>) => void;
  appendPriceHistory: (data: Record<string, PriceUpdate>) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
}

export const usePriceStore = create<PriceStore>()((set) => ({
  prices: {},
  priceHistory: {},
  chartHistory: {},
  connectionStatus: "disconnected",
  updatePrices: (data) =>
    set((state) => ({ prices: { ...state.prices, ...data } })),
  appendPriceHistory: (data) =>
    set((state) => {
      const newHistory = { ...state.priceHistory };
      const newChartHistory = { ...state.chartHistory };
      for (const [ticker, update] of Object.entries(data)) {
        // Sparkline history (number[])
        const existing = newHistory[ticker] || [];
        const updated = [...existing, update.price];
        newHistory[ticker] =
          updated.length > MAX_HISTORY_POINTS
            ? updated.slice(updated.length - MAX_HISTORY_POINTS)
            : updated;

        // Chart history (ChartDataPoint[])
        const existingChart = newChartHistory[ticker] || [];
        const newTime = Math.floor(update.timestamp);
        const lastPoint = existingChart[existingChart.length - 1];
        let updatedChart: ChartDataPoint[];
        if (lastPoint && lastPoint.time === newTime) {
          // Same second — update in place to avoid duplicate timestamps
          updatedChart = [...existingChart.slice(0, -1), { time: newTime, value: update.price }];
        } else {
          updatedChart = [...existingChart, { time: newTime, value: update.price }];
        }
        newChartHistory[ticker] =
          updatedChart.length > MAX_HISTORY_POINTS
            ? updatedChart.slice(updatedChart.length - MAX_HISTORY_POINTS)
            : updatedChart;
      }
      return { priceHistory: newHistory, chartHistory: newChartHistory };
    }),
  setConnectionStatus: (connectionStatus) => set({ connectionStatus }),
}));
