import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import { AgentProgressFeed } from "../components/query/AgentProgressFeed";
import { AnalysisResult } from "../components/results/AnalysisResult";
import { Button } from "../components/ui/Button";
import { Spinner } from "../components/ui/Spinner";
import { api } from "../lib/axios";

export default function QueryResult() {
  const { sessionId, queryId } = useParams<{ sessionId: string; queryId: string }>();
  const navigate = useNavigate();
  const [streamDone, setStreamDone] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);

  const { data: result, refetch } = useQuery({
    queryKey: ["query", queryId],
    queryFn: () => api.get(`/queries/${queryId}/`),
    enabled: !!queryId && streamDone,
    retry: 3
  });

  const isDraft = (result as any)?.intent?.startsWith("DRAFT_");

  if (streamError) {
    return (
      <div className="min-h-screen bg-surface-900 flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-purged">Pipeline failed: {streamError}</p>
          <Button onClick={() => navigate(`/session/${sessionId}`)}>Try Again</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-900 p-8 max-w-4xl mx-auto space-y-8">
      <button
        onClick={() => navigate(`/session/${sessionId}`)}
        className="text-gray-500 hover:text-gray-300 text-sm"
      >
        &lt;- Back
      </button>

      {!streamDone && queryId && (
        <AgentProgressFeed
          queryId={queryId}
          onComplete={() => {
            setStreamDone(true);
            void refetch();
          }}
          onFailed={setStreamError}
        />
      )}

      {streamDone && !result && <Spinner size="lg" />}

      {streamDone && result && !isDraft && <AnalysisResult result={result as any} />}

      {streamDone && result && isDraft && (
        <div className="space-y-4">
          <div
            className="lexai-document bg-surface-800 border border-surface-600 rounded-xl p-6"
            dangerouslySetInnerHTML={{
              __html: (result as any).result_payload?.draft_html ?? ""
            }}
          />
          <Button onClick={() => navigate(`/session/${sessionId}/query/${queryId}/review`)}>
            Proceed to Lawyer Review
          </Button>
        </div>
      )}
    </div>
  );
}
