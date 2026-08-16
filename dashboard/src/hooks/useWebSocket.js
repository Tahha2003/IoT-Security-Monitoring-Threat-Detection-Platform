import { useState, useEffect, useRef } from "react";

// NOTE: Update WS_URL to your backend IP before running
const WS_URL = process.env.REACT_APP_WS_URL || "ws://192.168.1.20:8000/ws";

export function useWebSocket() {
  const [messages, setMessages] = useState([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    function connect() {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        console.log("[WS] Connected");
      };

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          setMessages((prev) => [data, ...prev].slice(0, 500));
        } catch (_) {}
      };

      ws.onclose = () => {
        setConnected(false);
        console.log("[WS] Disconnected — reconnecting in 3s");
        setTimeout(connect, 3000);
      };

      ws.onerror = () => ws.close();
    }

    connect();
    return () => wsRef.current?.close();
  }, []);

  return { messages, connected };
}
