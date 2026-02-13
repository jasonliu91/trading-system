import {
  DecisionItem,
  Kline,
  MarketMindHistoryItem,
  MarketMindResponse,
  PerformanceResponse,
  PortfolioSnapshot,
  Timeframe
} from "@/lib/types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function fetchJSON<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export async function fetchKlines(timeframe: Timeframe, limit = 120): Promise<Kline[]> {
  const payload = await fetchJSON<{ items: Kline[] }>(`/api/klines?timeframe=${timeframe}&limit=${limit}`);
  return payload.items ?? [];
}

export async function fetchPortfolio(): Promise<PortfolioSnapshot> {
  return fetchJSON<PortfolioSnapshot>("/api/portfolio");
}

export async function fetchDecisions(limit = 20): Promise<DecisionItem[]> {
  const payload = await fetchJSON<{ items: DecisionItem[] }>(`/api/decisions?limit=${limit}`);
  return payload.items ?? [];
}

export async function fetchMarketMind(): Promise<MarketMindResponse> {
  return fetchJSON<MarketMindResponse>("/api/mind");
}

export async function updateMarketMind(
  marketMind: Record<string, unknown>,
  changedBy = "web_ui",
  changeSummary = "Updated from /mind page"
): Promise<MarketMindResponse> {
  const response = await fetch(`${API_BASE_URL}/api/mind`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      market_mind: marketMind,
      changed_by: changedBy,
      change_summary: changeSummary
    })
  });
  if (!response.ok) {
    throw new Error(`Failed to update market mind: ${response.status} ${response.statusText}`);
  }
  const payload = (await response.json()) as { market_mind: Record<string, unknown> };
  return {
    market_mind: payload.market_mind,
    prompt_preview: ""
  };
}

export async function fetchMarketMindHistory(limit = 20): Promise<MarketMindHistoryItem[]> {
  const payload = await fetchJSON<{ items: MarketMindHistoryItem[] }>(`/api/mind/history?limit=${limit}`);
  return payload.items ?? [];
}

export async function fetchPerformance(): Promise<PerformanceResponse> {
  return fetchJSON<PerformanceResponse>("/api/performance");
}
