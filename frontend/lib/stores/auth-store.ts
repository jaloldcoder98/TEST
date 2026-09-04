"use client";

import { create } from "zustand";

import type { User } from "@/lib/types";

/**
 * Session state, held **only in memory** (docs/DECISIONS.md D-12).
 *
 * Nothing here is persisted. The access token is short-lived and the refresh token never reaches
 * JavaScript at all — it lives in an httpOnly cookie the server sets (D-13). That is the whole
 * point: a reload does not restore the session from storage, it silently re-authenticates with
 * fresh `initData` from Telegram (D-15), so there is no long-lived credential sitting in
 * localStorage for an XSS bug to walk off with.
 *
 * `csrfToken` is the double-submit half of the CSRF pair (D-19): held here, echoed in
 * `X-CSRF-Token` on the two endpoints that authenticate from the cookie.
 */
interface AuthState {
  accessToken: string | null;
  csrfToken: string | null;
  user: User | null;
  setSession: (accessToken: string, csrfToken: string, user: User) => void;
  setUser: (user: User) => void;
  setTokens: (accessToken: string, csrfToken: string) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>()((set) => ({
  accessToken: null,
  csrfToken: null,
  user: null,
  setSession: (accessToken, csrfToken, user) => set({ accessToken, csrfToken, user }),
  setUser: (user) => set({ user }),
  setTokens: (accessToken, csrfToken) => set({ accessToken, csrfToken }),
  clear: () => set({ accessToken: null, csrfToken: null, user: null }),
}));
