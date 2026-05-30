import { create } from "zustand";
import { api } from "@/api/client";

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem("acg_token"),
  isAuthenticated: !!localStorage.getItem("acg_token"),
  login: async (email, password) => {
    const res = await api.post<{ access_token: string }>("/api/v1/auth/login", { email, password });
    const token = res.data.access_token;
    localStorage.setItem("acg_token", token);
    set({ token, isAuthenticated: true });
  },
  logout: () => {
    localStorage.removeItem("acg_token");
    set({ token: null, isAuthenticated: false });
  },
}));
