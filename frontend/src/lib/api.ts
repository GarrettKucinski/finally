import { toast } from "sonner";
import type {
  ApiError,
  ChatResponse,
  PortfolioResponse,
  SnapshotPoint,
  TradeRequest,
  TradeResponse,
  WatchlistItem,
} from "@/types/api";

export async function apiFetch<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    let err: ApiError;
    try {
      err = (await res.json()) as ApiError;
    } catch {
      err = { error: "Request failed", detail: `HTTP ${res.status}` };
    }
    toast.error(err.detail || err.error);
    throw err;
  }

  return res.json() as Promise<T>;
}

export function fetchPortfolio(): Promise<PortfolioResponse> {
  return apiFetch<PortfolioResponse>("/api/portfolio");
}

export function executeTrade(req: TradeRequest): Promise<TradeResponse> {
  return apiFetch<TradeResponse>("/api/portfolio/trade", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function fetchWatchlist(): Promise<WatchlistItem[]> {
  return apiFetch<WatchlistItem[]>("/api/watchlist");
}

export function addTicker(ticker: string): Promise<WatchlistItem> {
  return apiFetch<WatchlistItem>("/api/watchlist", {
    method: "POST",
    body: JSON.stringify({ ticker }),
  });
}

export async function removeTicker(ticker: string): Promise<void> {
  await apiFetch<void>(`/api/watchlist/${ticker}`, {
    method: "DELETE",
  });
}

export function fetchPortfolioHistory(): Promise<SnapshotPoint[]> {
  return apiFetch<SnapshotPoint[]>("/api/portfolio/history");
}

export function sendChat(message: string): Promise<ChatResponse> {
  return apiFetch<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}
