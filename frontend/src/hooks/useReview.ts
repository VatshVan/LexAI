import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../lib/axios";

export function useCompiledDocument(queryId: string | undefined) {
  return useQuery({
    queryKey: ["compiled", queryId],
    queryFn: () => api.get(`/queries/${queryId}/document/`),
    enabled: !!queryId,
    refetchInterval: 4000
  });
}

export function useApproveClause(queryId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (index: number) =>
      api.post(`/queries/${queryId}/document/clauses/${index}/approve/`, {}),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["compiled", queryId] })
  });
}

export function useApproveAll(queryId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post(`/queries/${queryId}/document/clauses/approve-all/`, {}),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["compiled", queryId] })
  });
}
