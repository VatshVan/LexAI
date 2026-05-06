import { useEffect } from "react";

import { BASE_URL } from "./axios";

export interface SSEEvent {
  event: string;
  agent?: string;
  duration_ms?: number;
  chunks_found?: number;
  status?: string;
  error?: string;
  total_claims?: number;
  score?: number;
  passed?: number;
  purged?: number;
  [key: string]: unknown;
}

export function useQueryStream(
  queryId: string | null,
  onEvent: (event: SSEEvent) => void,
  enabled = true
) {
  useEffect(() => {
    if (!queryId || !enabled) return;
    const es = new EventSource(`${BASE_URL}/queries/${queryId}/stream/`, {
      withCredentials: true
    });
    es.onmessage = (event) => {
      try {
        onEvent(JSON.parse(event.data));
      } catch {
        return;
      }
    };
    es.onerror = () => es.close();
    return () => es.close();
  }, [queryId, enabled, onEvent]);
}
