type Variant =
  | "verified"
  | "insufficient"
  | "purged"
  | "pending"
  | "running"
  | "default";

const styles: Record<Variant, string> = {
  verified: "bg-verified/20 text-verified",
  insufficient: "bg-flagged/20 text-flagged",
  purged: "bg-purged/20 text-purged",
  pending: "bg-surface-600 text-gray-400",
  running: "bg-blue-900/40 text-accent",
  default: "bg-surface-600 text-gray-300"
};

export function Badge({
  label,
  variant = "default"
}: {
  label: string;
  variant?: Variant;
}) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono ${styles[variant]}`}>
      {label}
    </span>
  );
}
