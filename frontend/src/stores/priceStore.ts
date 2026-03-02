import { create } from "zustand";
import type { PriceUpdate } from "@/types/api";

export type ConnectionStatus = "connected" | "reconnecting" | "disconnected";

interface PriceStore {
  prices: Record<string, PriceUpdate>;
  connectionStatus: ConnectionStatus;
  updatePrices: (data: Record<string, PriceUpdate>) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
}

export const usePriceStore = create<PriceStore>()((set) => ({
  prices: {},
  connectionStatus: "disconnected",
  updatePrices: (data) =>
    set((state) => ({ prices: { ...state.prices, ...data } })),
  setConnectionStatus: (connectionStatus) => set({ connectionStatus }),
}));
