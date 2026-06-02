import axios from "axios";
import { getApiBaseUrl } from "@/lib/apiBase";

export const api = axios.create({
  baseURL: getApiBaseUrl(),
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("acg_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 → redirect to login
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("acg_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);
