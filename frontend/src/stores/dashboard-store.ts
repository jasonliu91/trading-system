import { Timeframe } from "@/lib/types";
import { create } from "zustand";

interface DashboardStore {
  timeframe: Timeframe;
  autoRefresh: boolean;
  setTimeframe: (timeframe: Timeframe) => void;
  toggleAutoRefresh: () => void;
}

export const useDashboardStore = create<DashboardStore>((set) => ({
  timeframe: "1d",
  autoRefresh: true,
  setTimeframe: (timeframe) => set({ timeframe }),
  toggleAutoRefresh: () => set((state) => ({ autoRefresh: !state.autoRefresh }))
}));

