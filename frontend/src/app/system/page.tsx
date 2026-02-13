"use client";

import {
  fetchSystemHealth,
  fetchSystemStatus,
  pauseSystem,
  resumeSystem,
  triggerAnalysis
} from "@/lib/api";
import { SystemHealthResponse, SystemStatusResponse } from "@/lib/types";
import { useCallback, useEffect, useState } from "react";

function schedulerText(value: SystemStatusResponse["scheduler"] | SystemHealthResponse["scheduler"] | undefined): string {
  if (!value) {
    return "N/A";
  }
  if (typeof value === "string") {
    return value;
  }
  return value.status || "N/A";
}

export default function SystemPage() {
  const [status, setStatus] = useState<SystemStatusResponse | null>(null);
  const [health, setHealth] = useState<SystemHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [actionResult, setActionResult] = useState<string>("");

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const [statusPayload, healthPayload] = await Promise.all([fetchSystemStatus(), fetchSystemHealth()]);
      setStatus(statusPayload);
      setHealth(healthPayload);
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : "Failed to load system info");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const runAction = async (action: "trigger-analysis" | "pause" | "resume") => {
    setBusyAction(action);
    setError(null);
    setActionResult("");
    try {
      if (action === "trigger-analysis") {
        const payload = await triggerAnalysis();
        setActionResult(JSON.stringify(payload, null, 2));
      } else if (action === "pause") {
        const payload = await pauseSystem();
        setActionResult(JSON.stringify(payload, null, 2));
      } else if (action === "resume") {
        const payload = await resumeSystem();
        setActionResult(JSON.stringify(payload, null, 2));
      }
      await refresh();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "Action failed");
    } finally {
      setBusyAction("");
    }
  };

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-4 py-6 md:px-8 md:py-8">
      <header className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted">Operations</p>
          <h1 className="mt-1 text-2xl font-semibold text-text md:text-4xl">System Control</h1>
        </div>
        <button
          type="button"
          onClick={() => void refresh()}
          className="rounded-lg border border-border px-3 py-2 text-xs uppercase tracking-[0.14em] text-text hover:border-accent/60 md:self-end"
        >
          Refresh
        </button>
      </header>

      {error && <section className="rounded-xl border border-bear/40 bg-bear/10 p-3 text-sm text-red-100">{error}</section>}

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <article className="rounded-2xl border border-border bg-panel/70 p-4">
          <p className="text-xs uppercase tracking-[0.14em] text-muted">Service Health</p>
          <p className="mt-2 text-2xl font-semibold text-text">{health?.status || (loading ? "Loading..." : "N/A")}</p>
          <p className="mt-1 text-xs text-muted">service: {health?.service || "N/A"}</p>
        </article>

        <article className="rounded-2xl border border-border bg-panel/70 p-4">
          <p className="text-xs uppercase tracking-[0.14em] text-muted">Scheduler</p>
          <p className="mt-2 text-2xl font-semibold text-text">{schedulerText(status?.scheduler || health?.scheduler)}</p>
          <p className="mt-1 text-xs text-muted">interval: {status?.analysis_interval_hours ?? "N/A"}h</p>
        </article>

        <article className="rounded-2xl border border-border bg-panel/70 p-4">
          <p className="text-xs uppercase tracking-[0.14em] text-muted">Last Decision</p>
          <p className="mt-2 text-sm text-text">{status?.last_decision_at ? new Date(status.last_decision_at).toLocaleString() : "N/A"}</p>
          <p className="mt-1 text-xs text-muted">trading: {status?.trading || "N/A"}</p>
        </article>
      </section>

      <section className="rounded-2xl border border-border bg-panel/70 p-4">
        <h2 className="text-sm uppercase tracking-[0.14em] text-muted">Actions</h2>
        <div className="mt-3 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => void runAction("trigger-analysis")}
            disabled={busyAction.length > 0}
            className="rounded-lg border border-accent px-3 py-2 text-xs uppercase tracking-[0.14em] text-accent disabled:opacity-50"
          >
            {busyAction === "trigger-analysis" ? "Running..." : "Trigger Analysis"}
          </button>
          <button
            type="button"
            onClick={() => void runAction("pause")}
            disabled={busyAction.length > 0}
            className="rounded-lg border border-bear px-3 py-2 text-xs uppercase tracking-[0.14em] text-bear disabled:opacity-50"
          >
            {busyAction === "pause" ? "Pausing..." : "Pause Scheduler"}
          </button>
          <button
            type="button"
            onClick={() => void runAction("resume")}
            disabled={busyAction.length > 0}
            className="rounded-lg border border-bull px-3 py-2 text-xs uppercase tracking-[0.14em] text-bull disabled:opacity-50"
          >
            {busyAction === "resume" ? "Resuming..." : "Resume Scheduler"}
          </button>
        </div>
      </section>

      <section className="rounded-2xl border border-border bg-panel/70 p-4">
        <h2 className="text-sm uppercase tracking-[0.14em] text-muted">Action Result</h2>
        <pre className="mt-3 min-h-[180px] overflow-auto whitespace-pre-wrap rounded-lg border border-border/70 bg-bg/35 p-3 text-xs leading-6 text-muted">
          {actionResult || "No action executed yet."}
        </pre>
      </section>
    </main>
  );
}

