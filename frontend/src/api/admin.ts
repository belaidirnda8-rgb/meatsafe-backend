import { api } from "./client";

export interface Slaughterhouse {
  id: string;
  name: string;
  code: string;
  location?: string | null;
  created_at: string;
}

export interface CreateSlaughterhousePayload {
  name: string;
  code: string;
  location?: string;
}

export interface UpdateSlaughterhousePayload {
  name?: string;
  code?: string;
  location?: string | null;
}

export type Role = "admin" | "inspector";

export interface AdminUser {
  id: string;
  email: string;
  role: Role;
  slaughterhouse_id?: string | null;
  created_at: string;
}

export interface CreateUserPayload {
  email: string;
  password: string;
  role: Role;
  slaughterhouse_id?: string | null;
}

export const fetchSlaughterhouses = async (): Promise<Slaughterhouse[]> => {
  const res = await api.get<Slaughterhouse[]>("/slaughterhouses");
  return res.data;
};

export const createSlaughterhouse = async (
  payload: CreateSlaughterhousePayload
): Promise<Slaughterhouse> => {
  const res = await api.post<Slaughterhouse>("/slaughterhouses", payload);
  return res.data;
};

export const updateSlaughterhouse = async (
  id: string,
  payload: UpdateSlaughterhousePayload
): Promise<Slaughterhouse> => {
  const res = await api.put<Slaughterhouse>(`/slaughterhouses/${id}`, payload);
  return res.data;
};

export const fetchInspectors = async (
  slaughterhouse_id?: string
): Promise<AdminUser[]> => {
  const params: Record<string, string> = { role: "inspector" };
  if (slaughterhouse_id) {
    params.slaughterhouse_id = slaughterhouse_id;
  }
  const res = await api.get<AdminUser[]>("/users", { params });
  return res.data;
};

export const createInspector = async (
  payload: CreateUserPayload
): Promise<AdminUser> => {
  const res = await api.post<AdminUser>("/users", payload);
  return res.data;
};
