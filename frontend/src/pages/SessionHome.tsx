import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import { QueryInput } from "../components/query/QueryInput";
import { api } from "../lib/axios";

const SUGGESTIONS = [
  "Find contradictions in witness testimonies",
  "Extract a timeline of events from the FIR",
  "Draft a bail petition",
  "What charges is the accused facing?"
];

export default function SessionHome() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [template, setTemplate] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const { data: history = [] } = useQuery({
    queryKey: ["queries", sessionId],
    queryFn: () => api.get(`/sessions/${sessionId}/queries/`),
    enabled: !!sessionId,
    refetchInterval: 5000
  });

  const submit = async () => {
    if (!query.trim() || !sessionId) return;
    setSubmitting(true);
    try {
      const response: any = await api.post("/queries/", {
        session_id: sessionId,
        raw_query: query,
        template_name: template
      });
      navigate(`/session/${sessionId}/query/${response.query_id}`);
    } catch {
      return;
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface-900 flex">
      <aside className="w-64 bg-surface-800 border-r border-surface-600 p-4 space-y-2">
        <p className="text-xs text-gray-500 uppercase tracking-widest mb-4">Query History</p>
        {(history as any[]).map((item: any) => (
          <button
            key={item.query_id}
            onClick={() => navigate(`/session/${sessionId}/query/${item.query_id}`)}
            className="w-full text-left px-3 py-2 rounded-lg hover:bg-surface-700 text-sm text-gray-300 truncate"
          >
            {item.raw_query}
          </button>
        ))}
      </aside>

      <main className="flex-1 p-8 space-y-8">
        <QueryInput
          value={query}
          onChange={setQuery}
          onTemplateSelect={setTemplate}
          selectedTemplate={template}
          onSubmit={submit}
          submitting={submitting}
        />
        <div className="flex flex-wrap gap-2">
          {SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => setQuery(suggestion)}
              className="px-3 py-1.5 rounded-full text-sm border border-surface-600 text-gray-400 hover:border-accent hover:text-accent transition-colors"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </main>
    </div>
  );
}
