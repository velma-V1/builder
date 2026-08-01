// Structure-only placeholder — not installed, not run in this repository state.
//
// Zustand owns presentation-only state — nothing here is backend-sourced or authoritative.
// Mirrors factory.ui_studio.data_contracts.sidebar_presentation_contract(). If a future field here
// ever starts looking backend-shaped (e.g. "serverState", "record"), it belongs in a TanStack
// Query hook instead — see the STATE_OWNER_VIOLATION check in the backend contract.

import { create } from "zustand";

interface SidebarState {
  collapsed: boolean;
  activeTab: string;
  toggleCollapsed: () => void;
  setActiveTab: (tab: string) => void;
}

export const useSidebarStore = create<SidebarState>((set) => ({
  collapsed: false,
  activeTab: "overview",
  toggleCollapsed: () => set((s) => ({ collapsed: !s.collapsed })),
  setActiveTab: (tab) => set({ activeTab: tab }),
}));
