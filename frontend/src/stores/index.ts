// AutoPrism - Zustand Stores

// @ts-nocheck
import { create } from 'zustand';
import type { User, Panel, Subscription, DataSource, TechTag, FeedResponse } from '@/types';
import { auth, sources as sourcesApi, panels as panelsApi, feed, tags as tagsApi } from '@/lib/api';

// ============ Auth Store ============
interface AuthStore {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  loadUser: () => Promise<void>;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  token: localStorage.getItem('token'),
  isLoading: false,

  login: async (email, password) => {
    set({ isLoading: true });
    try {
      const data = await auth.login(email, password);
      localStorage.setItem('token', data.access_token);
      set({ token: data.access_token, isLoading: false });
      const user = await auth.me() as User;
      set({ user });
    } catch (e) {
      set({ isLoading: false });
      throw e;
    }
  },

  register: async (email, password) => {
    set({ isLoading: true });
    try {
      await auth.register(email, password);
      await auth.login(email, password).then(async (data) => {
        localStorage.setItem('token', data.access_token);
        set({ token: data.access_token, isLoading: false });
        const user = await auth.me() as User;
        set({ user });
      });
    } catch (e) {
      set({ isLoading: false });
      throw e;
    }
  },

  logout: () => {
    localStorage.removeItem('token');
    set({ user: null, token: null });
  },

  loadUser: async () => {
    const token = localStorage.getItem('token');
    if (!token) return;
    try {
      const user = await auth.me() as User;
      set({ user, token });
    } catch {
      localStorage.removeItem('token');
      set({ user: null, token: null });
    }
  },
}));

// ============ Panels Store ============
interface PanelsStore {
  panels: Panel[];
  isLoading: boolean;
  loadPanels: () => Promise<void>;
  addPanel: (data: Partial<Panel>) => Promise<Panel>;
  updatePanel: (id: string, data: Partial<Panel>) => Promise<void>;
  removePanel: (id: string) => Promise<void>;
}

export const usePanelsStore = create<PanelsStore>((set, get) => ({
  panels: [],
  isLoading: false,

  loadPanels: async () => {
    set({ isLoading: true });
    try {
      const token = localStorage.getItem('token');
      const panels = token
        ? await panelsApi.list() as Panel[]
        : await panelsApi.public() as Panel[];
      set({ panels, isLoading: false });
    } catch (e) {
      set({ isLoading: false });
      throw e;
    }
  },

  addPanel: async (data) => {
    const panel = await panelsApi.create(data as Parameters<typeof panelsApi.create>[0]) as Panel;
    set({ panels: [...get().panels, panel] });
    return panel;
  },

  updatePanel: async (id, data) => {
    await panelsApi.update(id, data);
    set({
      panels: get().panels.map((p) => (p.id === id ? { ...p, ...data } : p)),
    });
  },

  removePanel: async (id) => {
    await panelsApi.delete(id);
    set({ panels: get().panels.filter((p) => p.id !== id) });
  },
}));

// ============ Sources Store ============
interface SourcesStore {
  sources: DataSource[];
  subscriptions: Subscription[];
  isLoading: boolean;
  loadSources: () => Promise<void>;
  loadSubscriptions: () => Promise<void>;
  subscribe: (sourceId: string) => Promise<void>;
  unsubscribe: (sourceId: string) => Promise<void>;
}

export const useSourcesStore = create<SourcesStore>((set, get) => ({
  sources: [],
  subscriptions: [],
  isLoading: false,

  loadSources: async () => {
    set({ isLoading: true });
    try {
      const sources = await sourcesApi.list() as DataSource[];
      set({ sources, isLoading: false });
    } catch (e) {
      set({ isLoading: false });
      throw e;
    }
  },

  loadSubscriptions: async () => {
    try {
      const subs = await sourcesApi.subscriptions() as Subscription[];
      set({ subscriptions: subs });
    } catch (e) {
      set({ subscriptions: [] });
    }
  },

  subscribe: async (sourceId) => {
    const sub = await sourcesApi.subscribe(sourceId) as Subscription;
    set({ subscriptions: [...get().subscriptions, sub] });
  },

  unsubscribe: async (sourceId) => {
    await sourcesApi.unsubscribe(sourceId);
    set({ subscriptions: get().subscriptions.filter((s) => s.data_source_id !== sourceId) });
  },
}));

// ============ Feed Store ============
interface FeedStore {
  feeds: Map<string, FeedResponse>;
  isLoading: boolean;
  loadFeed: () => Promise<void>;
  refreshSource: (sourceId: string) => Promise<void>;
}

export const useFeedStore = create<FeedStore>((set, get) => ({
  feeds: new Map(),
  isLoading: false,

  loadFeed: async () => {
    set({ isLoading: true });
    try {
      // Always use public endpoint so panel data is consistent regardless of auth state
      const feeds = await feed.public() as FeedResponse[];
      const feedMap = new Map<string, FeedResponse>();
      feeds.forEach((f) => feedMap.set(f.data_source_id, f));
      set({ feeds: feedMap, isLoading: false });
    } catch (e) {
      set({ isLoading: false });
      throw e;
    }
  },

  refreshSource: async (sourceId) => {
    await feed.refresh(sourceId);
    const feedData = await feed.source(sourceId) as FeedResponse;
    set({ feeds: new Map(get().feeds).set(sourceId, feedData) });
  },
}));

// ============ Nebula Store ============
interface NebulaStore {
  tags: TechTag[];
  categories: string[];
  isLoading: boolean;
  loadTags: () => Promise<void>;
}

export const useNebulaStore = create<NebulaStore>((set) => ({
  tags: [],
  categories: [],
  isLoading: false,

  loadTags: async () => {
    set({ isLoading: true });
    try {
      const [tags, categories] = await Promise.all([
        tagsApi.withCounts(50) as Promise<TechTag[]>,
        tagsApi.categories() as Promise<string[]>,
      ]);
      set({ tags, categories, isLoading: false });
    } catch (e) {
      set({ isLoading: false });
    }
  },
}));

// ============ UI Store ============
type ViewMode = 'dashboard' | 'explore';

interface UIStore {
  viewMode: ViewMode;
  glassOpacity: number;
  setViewMode: (mode: ViewMode) => void;
  setGlassOpacity: (opacity: number) => void;
}

export const useUIStore = create<UIStore>((set) => ({
  viewMode: 'dashboard',
  glassOpacity: 0.3,

  setViewMode: (mode) => {
    set({ viewMode: mode });
    if (mode === 'explore') {
      set({ glassOpacity: 0 });
    } else {
      set({ glassOpacity: 0.3 });
    }
  },

  setGlassOpacity: (opacity) => set({ glassOpacity: opacity }),
}));

// ============ Signal Store ============
interface SignalStore {
  signals: any[];
  isLoading: boolean;
  loadSignals: () => Promise<void>;
}

export const useSignalStore = create<SignalStore>((set) => ({
  signals: [],
  isLoading: false,

  loadSignals: async () => {
    set({ isLoading: true });
    try {
      const res = await fetch('http://127.0.0.1:8001/api/v1/intel/');
      if (res.ok) {
        const data = await res.json();
        set({ signals: data, isLoading: false });
      }
    } catch (e) {
      console.error("Failed to load signals:", e);
      set({ isLoading: false });
    }
  }
}));