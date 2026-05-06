import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "../lib/axios";

export function useSessionQueries(sessionId: string | undefined) {
  return useQuery({
    queryKey: ["queries", sessionId],
    queryFn: () => api.get(`/sessions/${sessionId}/queries/`),
    enabled: !!sessionId,
    refetchInterval: 5000
  });
}

export function useSubmitQuery() {
  return useMutation({
    mutationFn: (payload: { session_id: string; raw_query: string; template_name?: string | null }) =>
      api.post("/queries/", payload)
  });
}

export function useQueryDetail(queryId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ["query", queryId],
    queryFn: () => api.get(`/queries/${queryId}/`),
    enabled: !!queryId && enabled
  });
}
