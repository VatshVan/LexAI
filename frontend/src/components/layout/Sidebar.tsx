import { ReactNode } from "react";

export function Sidebar({ children }: { children: ReactNode }) {
  return <aside className="w-64 bg-surface-800 border-r border-surface-600 p-4">{children}</aside>;
}
