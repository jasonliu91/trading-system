"use client";

import { API_BASE_URL } from "@/lib/api";
import { LivePayload } from "@/lib/types";
import { useEffect, useMemo, useState } from "react";

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
}

export function useLiveFeed(enabled: boolean): LiveFeedState {
  const [latest, setLatest] = useState<LivePayload | null>(null);
  const [status, setStatus] = useState<LiveFeedState["status"]>("closed");

  const wsURL = useMemo(() => `${toWebSocketURL(API_BASE_URL)}/ws/live`, []);

  useEffect(() => {
    if (!enabled) {
      setStatus("closed");
      return;
    }

    setStatus("connecting");
    const ws = new WebSocket(wsURL);

    ws.onopen = () => setStatus("open");
    ws.onerror = () => setStatus("error");
    ws.onclose = () => setStatus("closed");
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as LivePayload;
        setLatest(payload);
      } catch {
        // Ignore malformed payload.
      }
    };

    return () => {
      ws.close();
    };
  }, [enabled, wsURL]);

  return { latest, status };
}

