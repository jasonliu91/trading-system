"use client";

import { API_BASE_URL } from "@/lib/api";
import { LivePayload } from "@/lib/types";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

function toWebSocketURL(baseURL: string): string {
  if (baseURL.startsWith("https://")) {
    return baseURL.replace("https://", "wss://");
  }
  if (baseURL.startsWith("http://")) {
    return baseURL.replace("http://", "ws://");
  }
  return `ws://${baseURL}`;
}

interface LiveFeedState {
  latest: LivePayload | null;
  status: "connecting" | "open" | "closed" | "error";
  reconnectCount: number;
}

const MAX_RECONNECT_ATTEMPTS = 10;
const BASE_DELAY_MS = 1000;
const MAX_DELAY_MS = 30000;

export function useLiveFeed(enabled: boolean): LiveFeedState {
  const [latest, setLatest] = useState<LivePayload | null>(null);
  const [status, setStatus] = useState<LiveFeedState["status"]>("closed");
  const [reconnectCount, setReconnectCount] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const attemptRef = useRef(0);

  const wsURL = useMemo(() => `${toWebSocketURL(API_BASE_URL)}/ws/live`, []);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current !== null) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    setStatus("connecting");
    const ws = new WebSocket(wsURL);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("open");
      attemptRef.current = 0;
      setReconnectCount(0);
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as LivePayload;
        setLatest(payload);
      } catch {
        // Ignore malformed payload.
      }
    };

    ws.onerror = () => {
      setStatus("error");
    };

    ws.onclose = () => {
      setStatus("closed");
      wsRef.current = null;

      // Exponential backoff reconnection
      if (attemptRef.current < MAX_RECONNECT_ATTEMPTS) {
        const delay = Math.min(
          BASE_DELAY_MS * Math.pow(2, attemptRef.current),
          MAX_DELAY_MS
        );
        attemptRef.current += 1;
        setReconnectCount(attemptRef.current);

        reconnectTimerRef.current = setTimeout(() => {
          connect();
        }, delay);
      }
    };
  }, [wsURL]);

  useEffect(() => {
    if (!enabled) {
      clearReconnectTimer();
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setStatus("closed");
      attemptRef.current = 0;
      setReconnectCount(0);
      return;
    }

    connect();

    return () => {
      clearReconnectTimer();
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [enabled, connect, clearReconnectTimer]);

  // Pause WebSocket when tab is hidden to save resources
  useEffect(() => {
    const handleVisibility = () => {
      if (document.hidden) {
        clearReconnectTimer();
        if (wsRef.current) {
          wsRef.current.close();
          wsRef.current = null;
        }
      } else if (enabled && !wsRef.current) {
        attemptRef.current = 0;
        connect();
      }
    };

    document.addEventListener("visibilitychange", handleVisibility);
    return () => document.removeEventListener("visibilitychange", handleVisibility);
  }, [enabled, connect, clearReconnectTimer]);

  return { latest, status, reconnectCount };
}
