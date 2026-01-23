import * as zustand from "zustand";
import AsyncStorage from "@react-native-async-storage/async-storage";
import NetInfo from "@react-native-community/netinfo";
import { createSeizure, CreateSeizurePayload } from "../api/inspector";

export type OfflineSeizureStatus = "pending" | "synced" | "failed";

export interface OfflineSeizure {
  localId: string;
  payload: CreateSeizurePayload;
  status: OfflineSeizureStatus;
  error?: string;
}

interface OfflineQueueState {
  items: OfflineSeizure[];
  isOnline: boolean;
  addPending: (payload: CreateSeizurePayload) => void;
  markSynced: (localId: string) => void;
  markFailed: (localId: string, error?: string) => void;
  loadFromStorage: () => Promise<void>;
  syncAll: () => Promise<void>;
}

const STORAGE_KEY = "meatsafe_offline_seizures";

const createStore: any = (zustand as any).default || (zustand as any).create;

export const useOfflineQueue = create<OfflineQueueState>((set, get) => {
  // Abonnement réseau
  NetInfo.addEventListener((state) => {
    const online = !!state.isConnected && !!state.isInternetReachable;
    set({ isOnline: online });
    if (online) {
      void get().syncAll();
    }
  });

  const loadFromStorage = async () => {
    try {
      const stored = await AsyncStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed: OfflineSeizure[] = JSON.parse(stored);
        set({ items: parsed });
      }
    } catch (e) {
      // ignore pour MVP
    }
  };

  const persist = async (items: OfflineSeizure[]) => {
    try {
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    } catch (e) {
      // ignore
    }
  };

  const addPending = (payload: CreateSeizurePayload) => {
    const localId = `local-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const newItem: OfflineSeizure = {
      localId,
      payload,
      status: "pending",
    };
    set((state) => {
      const next = [...state.items, newItem];
      void persist(next);
      return { items: next };
    });
  };

  const markSynced = (localId: string) => {
    set((state) => {
      const next = state.items.filter((i) => i.localId !== localId);
      void persist(next);
      return { items: next };
    });
  };

  const markFailed = (localId: string, error?: string) => {
    set((state) => {
      const next = state.items.map((i) =>
        i.localId === localId ? { ...i, status: "failed", error } : i
      );
      void persist(next);
      return { items: next };
    });
  };

  const syncAll = async () => {
    const { items } = get();
    for (const item of items) {
      if (item.status !== "pending") continue;
      try {
        await createSeizure(item.payload);
        get().markSynced(item.localId);
      } catch (e) {
        get().markFailed(item.localId, "Erreur de synchronisation");
      }
    }
  };

  // état initial
  void loadFromStorage();

  return {
    items: [],
    isOnline: true,
    addPending,
    markSynced,
    markFailed,
    loadFromStorage,
    syncAll,
  };
});
