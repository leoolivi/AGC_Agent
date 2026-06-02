import { useCallback, useEffect, useRef, useState } from "react";
import { getApiBaseUrl, getWsBaseUrl } from "@/lib/apiBase";

export type ConnectionState = "connected" | "reconnecting" | "disconnected";

const BACKOFF = [1000, 2000, 4000, 8000, 16000, 30000];

interface UseWebSocketOptions {
  path?: string;
  onMessage?: (data: unknown) => void;
  enabled?: boolean;
}

export function useWebSocket({ path = "/ws/events", onMessage, enabled = true }: UseWebSocketOptions = {}) {
  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");
  const [useSSE, setUseSSE] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const attemptRef = useRef(0);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const baseUrl = getApiBaseUrl() || window.location.origin;
  const wsBase = getWsBaseUrl();

  const connectSSE = useCallback(() => {
    const token = localStorage.getItem("acg_token");
    if (!token) return;
    setUseSSE(true);
    setConnectionState("connected");
    const es = new EventSource(`${baseUrl}/api/v1/events/stream`, { withCredentials: true });
    es.onmessage = (ev) => {
      try {
        onMessageRef.current?.(JSON.parse(ev.data));
      } catch {
        /* ignore */
      }
    };
    es.onerror = () => {
      setConnectionState("disconnected");
      es.close();
    };
    return () => es.close();
  }, [baseUrl]);

  const connect = useCallback(() => {
    const token = localStorage.getItem("acg_token");
    if (!token || !enabled) return;

    setConnectionState("reconnecting");
    const url = `${wsBase}${path}?token=${encodeURIComponent(token)}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionState("connected");
      attemptRef.current = 0;
      setUseSSE(false);
    };

    ws.onmessage = (ev) => {
      try {
        onMessageRef.current?.(JSON.parse(ev.data));
      } catch {
        onMessageRef.current?.(ev.data);
      }
    };

    ws.onclose = () => {
      setConnectionState("disconnected");
      if (attemptRef.current >= 3) {
        connectSSE();
        return;
      }
      const delay = BACKOFF[Math.min(attemptRef.current, BACKOFF.length - 1)];
      attemptRef.current += 1;
      setTimeout(connect, delay);
    };

    ws.onerror = () => ws.close();
  }, [wsBase, path, enabled, connectSSE]);

  useEffect(() => {
    if (!enabled) return;
    connect();
    const interval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send("ping");
      }
    }, 30000);
    return () => {
      clearInterval(interval);
      const ws = wsRef.current;
      wsRef.current = null;
      if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CLOSING)) {
        ws.close();
      }
    };
  }, [connect, enabled]);

  return { connectionState, useSSE, reconnect: connect };
}
