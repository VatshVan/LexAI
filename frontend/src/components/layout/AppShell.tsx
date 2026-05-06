import { ReactNode } from "react";

export function AppShell({
  sidebar,
  children
}: {
  sidebar?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-surface-900 flex">
      {sidebar}
      <main className="flex-1">{children}</main>
    </div>
  );
}
