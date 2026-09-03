"use client";

/* TODO(webapp-first): TZ §14 — the store has no notion of whether onboarding is done, so nothing can route a new
 * Telegram user to the wizard instead of the dashboard. Add onboarding_completed (from
 * GET /users/me) once the backend field exists.
 * See docs/WEBAPP_FIRST_AUDIT.md for the full plan.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { User } from "@/lib/types";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  setSession: (accessToken: string, refreshToken: string, user: User) => void;
  setUser: (user: User) => void;
  setTokens: (accessToken: string, refreshToken: string) => void;
  clear: () => void;
}

// Persisted to localStorage (client-only) rather than an httpOnly cookie — this is a JWT SPA
// dashboard, not an SSR-authenticated app, so every protected page is a client component behind
// <AuthGuard> (see components/auth/auth-guard.tsx) rather than a server-side redirect.
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      setSession: (accessToken, refreshToken, user) => set({ accessToken, refreshToken, user }),
      setUser: (user) => set({ user }),
      setTokens: (accessToken, refreshToken) => set({ accessToken, refreshToken }),
      clear: () => set({ accessToken: null, refreshToken: null, user: null }),
    }),
    { name: "gym-auth" }
  )
);
