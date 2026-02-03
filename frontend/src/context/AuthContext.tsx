import React, {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
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

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // 🔄 تحميل الجلسة عند فتح التطبيق
  useEffect(() => {
    const init = async () => {
      try {
        const [storedToken, storedUser] = await Promise.all([
          AsyncStorage.getItem(STORAGE_KEY_TOKEN),
          AsyncStorage.getItem(STORAGE_KEY_USER),
        ]);

        if (storedToken && storedUser) {
          setAuthToken(storedToken);

          try {
            const meRes = await api.get("/users/me");
            const userData = meRes.data as AuthUser;

            setToken(storedToken);
            setUser(userData);

            await AsyncStorage.setItem(
              STORAGE_KEY_USER,
              JSON.stringify(userData)
            );
          } catch {
            await logout();
          }
        }
      } catch (e) {
        console.warn("Erreur init auth", e);
      } finally {
        setLoading(false);
      }
    };

    init();
  }, []);

  // 🔐 LOGIN
  const login = async ({ email, password }: LoginParams) => {
    const form = new URLSearchParams();
    form.append("grant_type", "password");
    form.append("username", email.trim());
    form.append("password", password);

    const body = form.toString();

    console.log("LOGIN URL:", "/auth/login (via api client)");
    console.log("LOGIN BODY:", body);

    try {
      const res = await api.post("/auth/login", body, {
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          Accept: "application/json",
        },
      });

      console.log("LOGIN OK:", res.status, res.data);

      const { access_token, user: userData } = res.data;

      setToken(access_token);
      setAuthToken(access_token);
      setUser(userData);

      await Promise.all([
        AsyncStorage.setItem(STORAGE_KEY_TOKEN, access_token),
        AsyncStorage.setItem(STORAGE_KEY_USER, JSON.stringify(userData)),
      ]);
    } catch (err: any) {
      console.log("LOGIN FAIL STATUS:", err?.response?.status);
      console.log("LOGIN FAIL DATA:", err?.response?.data);
      throw err;
    }
  };

  // 🚪 LOGOUT
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
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return ctx;
};