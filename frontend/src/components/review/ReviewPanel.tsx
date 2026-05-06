import { motion } from "framer-motion";

import { Button } from "../ui/Button";
import { ClauseChecklistItem } from "./ClauseChecklistItem";
import { ReviewProgressBar } from "./ReviewProgressBar";

interface Props {
  doc: any;
  onApprove: (index: number) => void;
  onApproveAll: () => void;
}

export function ReviewPanel({ doc, onApprove, onApproveAll }: Props) {
  const nullCount = doc.checklist?.filter((item: any) => item.is_null_field).length ?? 0;
  return (
    <div className="flex-1 p-6 overflow-y-auto space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Lawyer Review</h2>
        <Button
          variant="ghost"
          onClick={onApproveAll}
          disabled={doc.approved_clauses >= doc.total_clauses - nullCount}
        >
          Approve All Non-Null
        </Button>
      </div>

      <ReviewProgressBar
        approved={doc.approved_clauses}
        total={doc.total_clauses}
        nullCount={nullCount}
      />
      <p className="text-xs text-gray-500">
        {doc.approved_clauses} / {doc.total_clauses} clauses approved
      </p>

      <div className="space-y-3">
        {(doc.checklist ?? []).map((item: any) => (
          <motion.div key={item.clause_index} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <ClauseChecklistItem item={item} onApprove={onApprove} />
          </motion.div>
        ))}
      </div>
    </div>
  );
}
