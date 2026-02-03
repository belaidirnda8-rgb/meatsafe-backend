import axios from "axios";

// Backend unique (Render)
const API_URL = "https://meatsafe-backend-vg5c.onrender.com";

export const api = axios.create({
  baseURL: `${API_URL}/api`,
});

export const setAuthToken = (token: string | null) => {
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common.Authorization;
  }
};

// Logging global des erreurs API
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.log("API ERROR", {
      url: error?.config?.url,
      status: error?.response?.status,
      data: error?.response?.data,
    });
    return Promise.reject(error);
  }
);
