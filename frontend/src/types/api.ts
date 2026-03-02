export interface PriceUpdate {
  ticker: string;
  price: number;
  previous_price: number;
  timestamp: number;
  change: number;
  change_percent: number;
  direction: "up" | "down" | "flat";
}

export interface WatchlistItem {
  ticker: string;
  current_price: number | null;
  change: number | null;
  change_percent: number | null;
  direction: string | null;
  added_at: string | null;
}

export interface PositionDetail {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number | null;
  unrealized_pnl: number;
  pnl_percent: number;
}

export interface PortfolioResponse {
  cash_balance: number;
  total_value: number;
  positions: PositionDetail[];
}

export interface TradeRequest {
  ticker: string;
  side: "buy" | "sell";
  quantity: number;
}

export interface TradeResponse {
  ticker: string;
  side: string;
  quantity: number;
  price: number;
  total: number;
}

export interface SnapshotPoint {
  total_value: number;
  recorded_at: string;
}

export interface ApiError {
  error: string;
  detail: string;
}

export interface ChatTradeAction {
  ticker: string;
  side: string;
  quantity: number;
}

export interface ChatWatchlistAction {
  ticker: string;
  action: string;
}

export interface ChatExecutedTrade {
  ticker: string;
  side: string;
  quantity: number;
  price: number;
  total: number;
}

export interface ChatExecutedActions {
  watchlist_changes: ChatWatchlistAction[];
  errors: Array<{ type: string; detail: string; ticker: string }>;
}

export interface ChatResponse {
  message: string;
  proposed_trades: ChatTradeAction[];
  watchlist_changes: ChatWatchlistAction[];
  executed_actions: ChatExecutedActions;
}

export type ProposedTradeStatus = "pending" | "confirmed" | "dismissed" | "failed";

export interface ProposedTrade {
  ticker: string;
  side: string;
  quantity: number;
  status: ProposedTradeStatus;
  result?: ChatExecutedTrade;
  error?: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  executed_actions?: ChatExecutedActions;
  proposed_trades?: ProposedTrade[];
}
