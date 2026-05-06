import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../lib/axios";

export function useSessionDocuments(sessionId: string | null) {
  return useQuery<any[]>({
    queryKey: ["documents", sessionId],
    queryFn: async () => {
      if (!sessionId) return [];
      return (await api.get(`/sessions/${sessionId}/documents/`)) as any[];
    },
    enabled: !!sessionId,
    refetchInterval: 3000
  });
}

export function useCreateSession() {
  return useMutation({
    mutationFn: () => api.post("/sessions/", {})
  });
}

export function useUploadDocument(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { file: File; title: string; document_type: string }) => {
      const form = new FormData();
      form.append("file", payload.file);
      form.append("title", payload.title);
      form.append("document_type", payload.document_type);
      form.append("session_id", sessionId);
      return api.post("/documents/upload/", form, {
        headers: { "Content-Type": "multipart/form-data" }
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", sessionId] });
    }
  });
}
