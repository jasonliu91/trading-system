"use client";

import { fetchDecisions, fetchKlines, fetchPortfolio } from "@/lib/api";
import { DecisionItem, Kline, PortfolioSnapshot, Timeframe } from "@/lib/types";
import { useCallback, useEffect, useState } from "react";

interface DashboardDataState {
  klines: Kline[];
  portfolio: PortfolioSnapshot | null;
  decisions: DecisionItem[];
  loading: boolean;
  error: string | null;
  lastUpdated: string | null;
  refresh: () => Promise<void>;
}

export function useDashboardData(timeframe: Timeframe, autoRefresh: boolean): DashboardDataState {
  const [klines, setKlines] = useState<Kline[]>([]);
  const [portfolio, setPortfolio] = useState<PortfolioSnapshot | null>(null);
  const [decisions, setDecisions] = useState<DecisionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const [klineData, portfolioData, decisionData] = await Promise.all([
        fetchKlines(timeframe),
        fetchPortfolio(),
        fetchDecisions(30)
      ]);
      setKlines(klineData);
      setPortfolio(portfolioData);
      setDecisions(decisionData);
      setLastUpdated(new Date().toISOString());
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "Failed to fetch dashboard data");
    } finally {
      setLoading(false);
    }
  }, [timeframe]);

  useEffect(() => {
    setLoading(true);
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!autoRefresh) {
      return;
    }
    const timer = setInterval(() => {
      void refresh();
    }, 15000);
    return () => clearInterval(timer);
  }, [autoRefresh, refresh]);

  return {
    klines,
    portfolio,
    decisions,
    loading,
    error,
    lastUpdated,
    refresh
  };
}

