import { ReactNode } from "react";

export function Card({
  children,
  className = ""
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-xl border border-surface-600 bg-surface-800 ${className}`}>
      {children}
    </div>
  );
}
