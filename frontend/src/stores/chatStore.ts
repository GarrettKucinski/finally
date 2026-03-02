import { create } from "zustand";
import type { ChatMessage, ProposedTrade } from "@/types/api";
import { sendChat, executeTrade } from "@/lib/api";
import { usePortfolioStore } from "@/stores/portfolioStore";

interface ChatStore {
  messages: ChatMessage[];
  loading: boolean;
  send: (message: string) => Promise<void>;
  confirmTrade: (messageIndex: number, tradeIndex: number) => Promise<void>;
  dismissTrade: (messageIndex: number, tradeIndex: number) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatStore>()((set, get) => ({
  messages: [],
  loading: false,
  send: async (message: string) => {
    const userMessage: ChatMessage = { role: "user", content: message };
    set((state) => ({
      messages: [...state.messages, userMessage],
      loading: true,
    }));

    try {
      const res = await sendChat(message);

      const proposedTrades: ProposedTrade[] = (res.proposed_trades ?? []).map(
        (t) => ({
          ticker: t.ticker,
          side: t.side,
          quantity: t.quantity,
          status: "pending" as const,
        })
      );

      const assistantMessage: ChatMessage = {
        role: "assistant",
        content: res.message,
        executed_actions: res.executed_actions,
        proposed_trades: proposedTrades.length > 0 ? proposedTrades : undefined,
      };
      set((state) => ({
        messages: [...state.messages, assistantMessage],
        loading: false,
      }));
    } catch {
      set({ loading: false });
    }
  },

  confirmTrade: async (messageIndex: number, tradeIndex: number) => {
    const messages = get().messages;
    const msg = messages[messageIndex];
    const trade = msg?.proposed_trades?.[tradeIndex];
    if (!trade || trade.status !== "pending") return;

    try {
      const result = await executeTrade({
        ticker: trade.ticker,
        side: trade.side as "buy" | "sell",
        quantity: trade.quantity,
      });

      set((state) => {
        const updated = [...state.messages];
        const updatedTrades = [...(updated[messageIndex].proposed_trades ?? [])];
        updatedTrades[tradeIndex] = {
          ...updatedTrades[tradeIndex],
          status: "confirmed",
          result,
        };
        updated[messageIndex] = {
          ...updated[messageIndex],
          proposed_trades: updatedTrades,
        };
        return { messages: updated };
      });

      usePortfolioStore.getState().refresh();
    } catch (err: unknown) {
      const errorMessage =
        err && typeof err === "object" && "detail" in err
          ? String((err as { detail: string }).detail)
          : "Trade failed";

      set((state) => {
        const updated = [...state.messages];
        const updatedTrades = [...(updated[messageIndex].proposed_trades ?? [])];
        updatedTrades[tradeIndex] = {
          ...updatedTrades[tradeIndex],
          status: "failed",
          error: errorMessage,
        };
        updated[messageIndex] = {
          ...updated[messageIndex],
          proposed_trades: updatedTrades,
        };
        return { messages: updated };
      });
    }
  },

  dismissTrade: (messageIndex: number, tradeIndex: number) => {
    set((state) => {
      const updated = [...state.messages];
      const updatedTrades = [...(updated[messageIndex].proposed_trades ?? [])];
      updatedTrades[tradeIndex] = {
        ...updatedTrades[tradeIndex],
        status: "dismissed",
      };
      updated[messageIndex] = {
        ...updated[messageIndex],
        proposed_trades: updatedTrades,
      };
      return { messages: updated };
    });
  },

  clearMessages: () => set({ messages: [] }),
}));
