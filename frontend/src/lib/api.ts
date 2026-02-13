import { DecisionItem, Kline, PortfolioSnapshot, Timeframe } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

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

