import { motion } from "framer-motion";

interface Props {
  approved: number;
  total: number;
  nullCount: number;
}

export function ReviewProgressBar({ approved, total, nullCount }: Props) {
  const nonNull = total - nullCount;
  const pct = nonNull > 0 ? (approved / nonNull) * 100 : 0;
  const nullPct = total > 0 ? (nullCount / total) * 100 : 0;
  return (
    <div className="h-2 bg-surface-700 rounded-full overflow-hidden flex">
      <motion.div
        className="h-full bg-verified"
        animate={{ width: `${(pct * (100 - nullPct)) / 100}%` }}
        transition={{ type: "spring", stiffness: 120, damping: 20 }}
      />
      <div className="h-full bg-null-field/50" style={{ width: `${nullPct}%` }} />
    </div>
  );
}
