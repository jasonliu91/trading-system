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
  risk_check?: {
    approved: boolean;
    violations: string[];
    adjustments: string[];
  };
  [key: string]: unknown;
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
  input_hash?: string;
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

export interface MarketMindHistoryItem {
  id: number;
  changed_at: string;
  changed_by: string;
  change_summary: string;
  previous_state: Record<string, unknown>;
  new_state: Record<string, unknown>;
}

export interface MarketMindResponse {
  market_mind: Record<string, unknown>;
  prompt_preview: string;
}

export interface PerformanceMetricBundle {
  total_return_pct: number;
  max_drawdown_pct: number;
  win_rate: number;
  profit_factor: number;
}

export interface PerformancePoint {
  date: string;
  equity: number;
}

export interface PerformanceResponse {
  equity_curve: PerformancePoint[];
  metrics: PerformanceMetricBundle;
}

export interface LivePayload {
  timestamp: string;
  symbol: string;
  price: number;
  latest_decision: string | null;
  latest_decision_id: number | null;
}

export interface SystemStatusResponse {
  trading: string;
  scheduler: { status: string } | string;
  data_pipeline: string;
  agent: string;
  analysis_interval_hours: number;
  last_decision_at: string | null;
}

export interface SystemHealthResponse {
  status: string;
  service: string;
  scheduler?: { status: string } | string;
}
