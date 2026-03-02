"use client";

import { useEffect, useRef } from "react";
import { usePriceStore } from "@/stores/priceStore";

export function useSSE() {
  const updatePrices = usePriceStore((s) => s.updatePrices);
  const setConnectionStatus = usePriceStore((s) => s.setConnectionStatus);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const es = new EventSource("/api/stream/prices");
    eventSourceRef.current = es;

    es.onopen = () => {
      setConnectionStatus("connected");
    };

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        updatePrices(data);
      } catch {
        // Ignore malformed SSE data
      }
    };

    es.onerror = () => {
      if (es.readyState === EventSource.CONNECTING) {
        setConnectionStatus("reconnecting");
      } else {
        setConnectionStatus("disconnected");
      }
    };

    return () => {
      es.close();
      setConnectionStatus("disconnected");
    };
  }, [updatePrices, setConnectionStatus]);
}
