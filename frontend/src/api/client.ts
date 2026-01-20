import axios from "axios";

const BASE_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

if (!BASE_URL) {
  console.warn("EXPO_PUBLIC_BACKEND_URL is not defined");
}

export const api = axios.create({
  baseURL: BASE_URL ? `${BASE_URL}/api` : "/api",
});

export const setAuthToken = (token: string | null) => {
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common.Authorization;
  }
};
