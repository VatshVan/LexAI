import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { DocumentCard } from "../components/documents/DocumentCard";
import { UploadZone } from "../components/documents/UploadZone";
import { Button } from "../components/ui/Button";
import { api } from "../lib/axios";
import { useSessionStore } from "../stores/sessionStore";

export default function NewSession() {
  const navigate = useNavigate();
  const { activeSessionId, setSession } = useSessionStore();
  const [sessionId, setSessionId] = useState<string | null>(activeSessionId);
  const [creating, setCreating] = useState(false);

  const { data: docs = [] } = useQuery<any[]>({
    queryKey: ["documents", sessionId],
    queryFn: async () => {
      if (!sessionId) return [];
      return (await api.get(`/sessions/${sessionId}/documents/`)) as any[];
    },
    enabled: !!sessionId,
    refetchInterval: 3000
  });

  const createSession = async () => {
    setCreating(true);
    try {
      const response: any = await api.post("/sessions/", {});
      const sid = response.session_id ?? response.id;
      setSession(sid);
      setSessionId(sid);
    } catch {
      return;
    } finally {
      setCreating(false);
    }
  };

  const readyCount = (docs as any[]).filter((doc: any) => doc.status === "READY").length;

  return (
    <div className="min-h-screen bg-surface-900 flex flex-col items-center justify-center p-8">
      <div className="w-full max-w-xl space-y-8">
        <div>
          <h1 className="text-3xl font-semibold text-white font-mono">LexAI</h1>
          <p className="text-gray-400 mt-1">Algorithmic Paralegal for Indian Lawyers</p>
        </div>

        {!sessionId ? (
          <Button onClick={createSession} loading={creating}>
            Start New Case Session
          </Button>
        ) : (
          <>
            <UploadZone sessionId={sessionId} />
            <div className="space-y-2">
              {(docs as any[]).map((doc: any) => (
                <DocumentCard key={doc.document_id} document={doc} />
              ))}
            </div>
            {readyCount > 0 && (
              <Button onClick={() => navigate(`/session/${sessionId}`)}>
                Start Querying ({readyCount} document{readyCount > 1 ? "s" : ""} ready)
              </Button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
