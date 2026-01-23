import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
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

interface OfflineQueueContextValue {
  items: OfflineSeizure[];
  isOnline: boolean;
  addPending: (payload: CreateSeizurePayload) => void;
  markSynced: (localId: string) => void;
  markFailed: (localId: string, error?: string) => void;
  loadFromStorage: () => Promise<void>;
  syncAll: () => Promise<void>;
}

const STORAGE_KEY = "meatsafe_offline_seizures";

const OfflineQueueContext = createContext<OfflineQueueContextValue | undefined>(
  undefined
);

export const OfflineQueueProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [items, setItems] = useState<OfflineSeizure[]>([]);
  const [isOnline, setIsOnline] = useState(true);

  const persist = useCallback(async (next: OfflineSeizure[]) => {
    try {
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // ignore for MVP
    }
  }, []);

  const loadFromStorage = useCallback(async () => {
    try {
      const stored = await AsyncStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed: OfflineSeizure[] = JSON.parse(stored);
        setItems(parsed);
      }
    } catch {
      // ignore for MVP
    }
  }, []);

  useEffect(() => {
    void loadFromStorage();
  }, [loadFromStorage]);

  const addPending = useCallback(
    (payload: CreateSeizurePayload) => {
      const localId = `local-${Date.now()}-${Math.random()
        .toString(36)
        .slice(2, 8)}`;
      const newItem: OfflineSeizure = {
        localId,
        payload,
        status: "pending",
      };
      setItems((prev) => {
        const next = [...prev, newItem];
        void persist(next);
        return next;
      });
    },
    [persist]
  );

  const markSynced = useCallback(
    (localId: string) => {
      setItems((prev) => {
        const next = prev.filter((i) => i.localId !== localId);
        void persist(next);
        return next;
      });
    },
    [persist]
  );

  const markFailed = useCallback(
    (localId: string, error?: string) => {
      setItems((prev) => {
        const next = prev.map((i) =>
          i.localId === localId ? { ...i, status: "failed", error } : i
        );
        void persist(next);
        return next;
      });
    },
    [persist]
  );

  const syncAll = useCallback(async () => {
    const currentItems = [...items];
    for (const item of currentItems) {
      if (item.status !== "pending") continue;
      try {
        await createSeizure(item.payload);
        markSynced(item.localId);
      } catch {
        markFailed(item.localId, "Erreur de synchronisation");
      }
    }
  }, [items, markFailed, markSynced]);

  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener((state) => {
      const online = !!state.isConnected && !!state.isInternetReachable;
      setIsOnline(online);
      if (online) {
        void syncAll();
      }
    });
    return unsubscribe;
  }, [syncAll]);

  const value: OfflineQueueContextValue = {
    items,
    isOnline,
    addPending,
    markSynced,
    markFailed,
    loadFromStorage,
    syncAll,
  };

  return (
    <OfflineQueueContext.Provider value={value}>
      {children}
    </OfflineQueueContext.Provider>
  );
};

export const useOfflineQueue = (): OfflineQueueContextValue => {
  const ctx = useContext(OfflineQueueContext);
  if (!ctx) {
    throw new Error("useOfflineQueue doit être utilisé dans un OfflineQueueProvider");
  }
  return ctx;
};
