import { create } from "zustand";
import type { PositionDetail } from "@/types/api";
import { fetchPortfolio } from "@/lib/api";

interface PortfolioStore {
  cashBalance: number;
  totalValue: number;
  positions: PositionDetail[];
  loading: boolean;
  refresh: () => Promise<void>;
}

export const usePortfolioStore = create<PortfolioStore>()((set) => ({
  cashBalance: 10000,
  totalValue: 10000,
  positions: [],
  loading: false,
  refresh: async () => {
    set({ loading: true });
    try {
      const data = await fetchPortfolio();
      set({
        cashBalance: data.cash_balance,
        totalValue: data.total_value,
        positions: data.positions,
        loading: false,
      });
    } catch {
      set({ loading: false });
    }
  },
}));
