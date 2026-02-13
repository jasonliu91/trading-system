export type Timeframe = "1h" | "4h" | "1d";

export interface Kline {
  symbol: string;
  timeframe: Timeframe;
  open_time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface DecisionReasoning {
  mind_alignment?: string;
  bias_check?: string;
  final_logic?: string;
}

export interface DecisionItem {
  id: number;
  timestamp: string;
  decision: "buy" | "sell" | "hold";
  position_size_pct: number;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  confidence: number;
  reasoning: DecisionReasoning;
  model_used: string;
}

export interface PortfolioPosition {
  symbol: string;
  side: "long";
  quantity: number;
  entry_price: number;
  mark_price: number;
  unrealized_pnl: number;
}

export interface PortfolioSnapshot {
  symbol: string;
  mark_price: number;
  balance: number;
  equity: number;
  available: number;
  exposure_pct: number;
  daily_pnl_pct: number;
  positions: PortfolioPosition[];
}

