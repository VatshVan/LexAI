import { AlertTriangle, Check } from "lucide-react";

import { Badge } from "../ui/Badge";

export function ClauseChecklistItem({
  item,
  onApprove
}: {
  item: any;
  onApprove: (index: number) => void;
}) {
  return (
    <div
      className={`p-4 rounded-lg border ${
        item.is_null_field
          ? "border-null-field/50 bg-null-field/5"
          : item.is_approved
          ? "border-surface-600 opacity-50"
          : "border-surface-600 bg-surface-800"
      }`}
    >
      <div className="flex items-start gap-3">
        {!item.is_null_field ? (
          <button
            onClick={() => !item.is_approved && onApprove(item.clause_index)}
            className={`mt-0.5 w-5 h-5 rounded border flex-shrink-0 flex items-center justify-center ${
              item.is_approved
                ? "bg-verified border-verified"
                : "border-surface-600 hover:border-accent"
            }`}
          >
            {item.is_approved && <Check size={12} className="text-white" />}
          </button>
        ) : (
          <AlertTriangle size={16} className="text-null-field mt-0.5 flex-shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-200">{item.clause_text}</p>
          <div className="flex items-center gap-2 mt-1">
            {item.citation_string && (
              <span className="text-xs font-mono text-gray-500">{item.citation_string}</span>
            )}
            <Badge
              label={item.verification_verdict || "UNKNOWN"}
              variant={
                item.verification_verdict === "VERIFIED" ||
                item.verification_verdict === "EXTERNALLY_VERIFIED"
                  ? "verified"
                  : item.verification_verdict === "INSUFFICIENT"
                  ? "insufficient"
                  : "pending"
              }
            />
            {item.is_null_field && (
              <span className="text-xs text-null-field">Required - fill manually</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
