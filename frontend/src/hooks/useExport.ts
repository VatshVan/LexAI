import { useQuery } from "@tanstack/react-query";

import { api } from "../lib/axios";

export function useExportStatus(queryId: string | undefined, polling = true) {
  return useQuery({
    queryKey: ["export-status", queryId],
    queryFn: () => api.get(`/queries/${queryId}/document/export/status/`),
    enabled: !!queryId,
    refetchInterval: polling ? 5000 : false
  });
}
