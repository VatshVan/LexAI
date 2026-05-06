import { useQuery } from "@tanstack/react-query";
import { FileText } from "lucide-react";

import { api } from "../../lib/axios";
import { Badge } from "../ui/Badge";

const STATUS_STEPS = [
  "UPLOADED",
  "OCR_PROCESSING",
  "OCR_COMPLETE",
  "CHUNKING",
  "EMBEDDING",
  "READY",
  "FAILED"
];

export function DocumentCard({ document }: { document: any }) {
  const { data } = useQuery({
    queryKey: ["document", document.document_id],
    queryFn: () => api.get(`/documents/${document.document_id}/status/`),
    refetchInterval:
      document.status === "READY" || document.status === "FAILED" ? false : 2000,
    initialData: document
  });
  const doc = { ...document, ...(data as any) };
  const stepIndex = STATUS_STEPS.indexOf(doc.status);

  return (
    <div className="flex items-center gap-3 p-3 bg-surface-800 border border-surface-600 rounded-lg">
      <FileText size={18} className="text-gray-500 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-200 truncate">{doc.title}</p>
        <div className="flex gap-1 mt-1">
          {STATUS_STEPS.slice(0, -1).map((step, index) => (
            <div
              key={step}
              className={`h-1 flex-1 rounded-full ${
                index < stepIndex
                  ? "bg-verified"
                  : index === stepIndex
                  ? "bg-accent animate-pulse"
                  : "bg-surface-600"
              }`}
            />
          ))}
        </div>
      </div>
      <Badge
        label={doc.status}
        variant={
          doc.status === "READY"
            ? "verified"
            : doc.status === "FAILED"
            ? "purged"
            : "running"
        }
      />
    </div>
  );
}
