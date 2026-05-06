import { create } from "zustand";

interface ReviewState {
  optimistic: Record<string, Set<number>>;
  approve: (docId: string, index: number) => void;
  reset: (docId: string) => void;
}

export const useReviewStore = create<ReviewState>((set) => ({
  optimistic: {},
  approve: (docId, index) =>
    set((state) => ({
      optimistic: {
        ...state.optimistic,
        [docId]: new Set([...(state.optimistic[docId] ?? []), index])
      }
    })),
  reset: (docId) =>
    set((state) => ({
      optimistic: { ...state.optimistic, [docId]: new Set() }
    }))
}));
