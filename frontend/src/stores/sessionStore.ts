import { create } from "zustand";
import { persist } from "zustand/middleware";

interface SessionState {
  activeSessionId: string | null;
  setSession: (id: string) => void;
  clearSession: () => void;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      activeSessionId: null,
      setSession: (id) => set({ activeSessionId: id }),
      clearSession: () => set({ activeSessionId: null })
    }),
    { name: "lexai-session" }
  )
);
