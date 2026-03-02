import { create } from "zustand";
import type { ChatMessage } from "@/types/api";
import { sendChat } from "@/lib/api";
import { usePortfolioStore } from "@/stores/portfolioStore";

interface ChatStore {
  messages: ChatMessage[];
  loading: boolean;
  send: (message: string) => Promise<void>;
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
      const assistantMessage: ChatMessage = {
        role: "assistant",
        content: res.message,
        executed_actions: res.executed_actions,
      };
      set((state) => ({
        messages: [...state.messages, assistantMessage],
        loading: false,
      }));

      if (res.executed_actions?.trades?.length > 0) {
        usePortfolioStore.getState().refresh();
      }
    } catch {
      set({ loading: false });
    }
  },
  clearMessages: () => set({ messages: [] }),
}));
