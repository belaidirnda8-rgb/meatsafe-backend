import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { api, setAuthToken } from "../api/client";

export type Role = "admin" | "inspector";

export interface AuthUser {
  id: string;
  email: string;
  role: Role;
  slaughterhouse_id?: string | null;
}

interface LoginParams {
  email: string;
  password: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
  login: (params: LoginParams) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const STORAGE_KEY_TOKEN = "meatsafe_token";
const STORAGE_KEY_USER = "meatsafe_user";

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const init = async () => {
      try {
        const [storedToken, storedUser] = await Promise.all([
          AsyncStorage.getItem(STORAGE_KEY_TOKEN),
          AsyncStorage.getItem(STORAGE_KEY_USER),
        ]);

        if (storedToken && storedUser) {
          // Tenter de valider le token auprès du backend
          setAuthToken(storedToken);
          try {
            const meRes = await api.get("/users/me");
            const userData = meRes.data as AuthUser;
            setToken(storedToken);
            setUser(userData);
            await AsyncStorage.setItem(STORAGE_KEY_USER, JSON.stringify(userData));
          } catch (e) {
            // Token invalide ou backend injoignable: forcer la reconnexion
            console.warn("Token invalide ou expiré, nettoyage de la session", e);
            setToken(null);
            setUser(null);
            setAuthToken(null);
            await Promise.all([
              AsyncStorage.removeItem(STORAGE_KEY_TOKEN),
              AsyncStorage.removeItem(STORAGE_KEY_USER),
            ]);
          }
        }
      } catch (error) {
        console.warn("Erreur lors du chargement du token", error);
      } finally {
        setLoading(false);
      }
    };

    void init();
  }, []);

  const login = async ({ email, password }: LoginParams) => {
    try {
      const body =
        `username=${encodeURIComponent(email.trim())}` +
        `&password=${encodeURIComponent(password.trim())}`;

      const baseUrl = process.env.EXPO_PUBLIC_BACKEND_URL;
      const url = baseUrl
        ? `${baseUrl}/api/auth/login`
        : "/api/auth/login";

      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          Accept: "application/json",
        },
        body,
      });

      if (!response.ok) {
        const text = await response.text().catch(() => "");
        console.error("Erreur de connexion fetch", response.status, text);
        throw new Error(`Status ${response.status}`);
      }

      const data = await response.json();
      const { access_token, user: userData } = data;

      setToken(access_token);
      setAuthToken(access_token);
      setUser(userData);

      await Promise.all([
        AsyncStorage.setItem(STORAGE_KEY_TOKEN, access_token),
        AsyncStorage.setItem(STORAGE_KEY_USER, JSON.stringify(userData)),
      ]);
    } catch (error) {
      console.error("Erreur de connexion", error);
      throw error;
    }
  };

  const logout = async () => {
    setUser(null);
    setToken(null);
    setAuthToken(null);
    await Promise.all([
      AsyncStorage.removeItem(STORAGE_KEY_TOKEN),
      AsyncStorage.removeItem(STORAGE_KEY_USER),
    ]);
  };

  const value = useMemo(
    () => ({ user, token, loading, login, logout }),
    [user, token, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth doit être utilisé dans un AuthProvider");
  }
  return ctx;
};
