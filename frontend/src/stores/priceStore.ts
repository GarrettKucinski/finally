import { create } from "zustand";
import type { PriceUpdate } from "@/types/api";

export type ConnectionStatus = "connected" | "reconnecting" | "disconnected";

const MAX_HISTORY_POINTS = 50;

interface PriceStore {
  prices: Record<string, PriceUpdate>;
  priceHistory: Record<string, number[]>;
  connectionStatus: ConnectionStatus;
  updatePrices: (data: Record<string, PriceUpdate>) => void;
  appendPriceHistory: (data: Record<string, PriceUpdate>) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
}

export const usePriceStore = create<PriceStore>()((set) => ({
  prices: {},
  priceHistory: {},
  connectionStatus: "disconnected",
  updatePrices: (data) =>
    set((state) => ({ prices: { ...state.prices, ...data } })),
  appendPriceHistory: (data) =>
    set((state) => {
      const newHistory = { ...state.priceHistory };
      for (const [ticker, update] of Object.entries(data)) {
        const existing = newHistory[ticker] || [];
        const updated = [...existing, update.price];
        newHistory[ticker] =
          updated.length > MAX_HISTORY_POINTS
            ? updated.slice(updated.length - MAX_HISTORY_POINTS)
            : updated;
      }
      return { priceHistory: newHistory };
    }),
  setConnectionStatus: (connectionStatus) => set({ connectionStatus }),
}));
