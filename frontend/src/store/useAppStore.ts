import { create } from "zustand";
import { api, type Identity, type Session } from "../api/client";

export type DomainKey = "cyber" | "health" | "fintech";

type Row = Record<string, any>;

export interface TickerItem {
  id: string;
  domain: DomainKey;
  label: string;
  detail: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  ts: number;
}

interface AppState {
  token: string | null;
  identity: Identity | null;
  authError: string | null;
  loading: boolean;

  activeTab: DomainKey | null;
  data: Record<DomainKey, Row[]>;
  selected: Record<DomainKey, Row | null>;
  ticker: TickerItem[];

  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  setActiveTab: (tab: DomainKey) => void;
  selectRow: (domain: DomainKey, row: Row | null) => void;
  upsert: (domain: DomainKey, idField: string, rows: Row[]) => void;
  pushTicker: (items: TickerItem[]) => void;
}

const MAX_ROWS = 2000;
const MAX_TICKER = 120;

export const useAppStore = create<AppState>((set) => ({
  token: null,
  identity: null,
  authError: null,
  loading: false,

  activeTab: null,
  data: { cyber: [], health: [], fintech: [] },
  selected: { cyber: null, health: null, fintech: null },
  ticker: [],

  login: async (username, password) => {
    set({ loading: true, authError: null });
    try {
      const session: Session = await api.login(username, password);
      const identity = await api.me(session.access_token);
      const firstTab = (identity.tabs.find((t) => t !== "admin") as DomainKey) ?? null;
      set({ token: session.access_token, identity, activeTab: firstTab, loading: false });
    } catch (err: any) {
      set({ authError: err?.message ?? "Login failed", loading: false });
    }
  },

  logout: () =>
    set({
      token: null,
      identity: null,
      activeTab: null,
      data: { cyber: [], health: [], fintech: [] },
      selected: { cyber: null, health: null, fintech: null },
      ticker: [],
    }),

  setActiveTab: (tab) => set({ activeTab: tab }),

  selectRow: (domain, row) => set((s) => ({ selected: { ...s.selected, [domain]: row } })),

  upsert: (domain, idField, rows) =>
    set((s) => {
      const index = new Map<string, Row>();
      for (const existing of s.data[domain]) index.set(existing[idField], existing);
      for (const incoming of rows) {
        if (!incoming || incoming[idField] === undefined) continue;
        index.set(incoming[idField], incoming);
      }
      const merged = Array.from(index.values()).slice(-MAX_ROWS);
      return { data: { ...s.data, [domain]: merged } };
    }),

  pushTicker: (items) =>
    set((s) => ({ ticker: [...items, ...s.ticker].slice(0, MAX_TICKER) })),
}));

export const hasScope = (scope: string) => {
  const id = useAppStore.getState().identity;
  return !!id && id.scopes.includes(scope);
};
