import { Download } from "lucide-react";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "../../lib/axios";
import { Button } from "../ui/Button";

interface Props {
  queryId: string;
  doc: any;
}

export function ExportPanel({ queryId, doc }: Props) {
  const [downloading, setDownloading] = useState<string | null>(null);
  const { data: status } = useQuery({
    queryKey: ["export-status", queryId],
    queryFn: () => api.get(`/queries/${queryId}/document/export/status/`),
    refetchInterval: doc.can_export ? false : 5000
  });
  const exportStatus = status as any;

  const download = async (fmt: "pdf" | "docx") => {
    setDownloading(fmt);
    try {
      const base = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
      const response = await fetch(`${base}/queries/${queryId}/document/export/${fmt}/`, {
        credentials: "include"
      });
      if (!response.ok) throw new Error("Export blocked");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `lexai-document.${fmt}`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch {
      return;
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="w-64 bg-surface-800 border-l border-surface-600 p-6 space-y-4">
      <h3 className="font-semibold text-white">Export</h3>
      {exportStatus?.can_export ? (
        <div className="space-y-3">
          <div className="bg-verified/10 border border-verified/30 rounded-lg p-3 text-xs text-verified">
            Review complete - ready to export
          </div>
          <Button className="w-full" onClick={() => download("pdf")} loading={downloading === "pdf"}>
            <Download size={14} /> Download PDF
          </Button>
          <Button
            variant="ghost"
            className="w-full"
            onClick={() => download("docx")}
            loading={downloading === "docx"}
          >
            <Download size={14} /> Download DOCX
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="bg-surface-700 rounded-lg p-3 text-xs text-gray-400 space-y-1">
            {exportStatus?.blockers?.pending_approvals > 0 && (
              <p>- {exportStatus.blockers.pending_approvals} clause(s) need approval</p>
            )}
            {exportStatus?.blockers?.null_fields_unfilled > 0 && (
              <p>- {exportStatus.blockers.null_fields_unfilled} required field(s) unfilled</p>
            )}
          </div>
          <Button className="w-full" disabled title="Complete review to export">
            <Download size={14} /> Export
          </Button>
        </div>
      )}
    </div>
  );
}
