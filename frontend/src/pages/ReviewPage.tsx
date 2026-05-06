import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { ExportPanel } from "../components/review/ExportPanel";
import { ReviewPanel } from "../components/review/ReviewPanel";
import { Spinner } from "../components/ui/Spinner";
import { api } from "../lib/axios";

export default function ReviewPage() {
  const { queryId } = useParams<{ queryId: string }>();
  const queryClient = useQueryClient();

  const { data: doc, isLoading } = useQuery({
    queryKey: ["compiled", queryId],
    queryFn: () => api.get(`/queries/${queryId}/document/`),
    enabled: !!queryId,
    refetchInterval: 4000
  });

  const approveClause = useMutation({
    mutationFn: (index: number) =>
      api.post(`/queries/${queryId}/document/clauses/${index}/approve/`, {}),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["compiled", queryId] })
  });

  const approveAll = useMutation({
    mutationFn: () => api.post(`/queries/${queryId}/document/clauses/approve-all/`, {}),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["compiled", queryId] })
  });

  if (isLoading || !doc) {
    return (
      <div className="min-h-screen bg-surface-900 flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  const documentData = doc as any;

  return (
    <div className="min-h-screen bg-surface-900 flex">
      <div className="w-72 bg-surface-800 border-r border-surface-600 p-4 overflow-y-auto">
        <p className="text-xs text-gray-500 uppercase tracking-widest mb-4">Document Preview</p>
        <div
          className="lexai-document text-xs text-gray-300 space-y-2"
          dangerouslySetInnerHTML={{ __html: documentData.assembled_html }}
        />
      </div>

      <ReviewPanel
        doc={documentData}
        onApprove={(index) => approveClause.mutate(index)}
        onApproveAll={() => approveAll.mutate()}
      />

      <ExportPanel queryId={queryId!} doc={documentData} />
    </div>
  );
}
