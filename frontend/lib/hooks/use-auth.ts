"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api-client";
import { useAuthStore } from "@/lib/stores/auth-store";
import type { SessionResponse, User } from "@/lib/types";

async function fetchMe(): Promise<User> {
  return api.get<User>("/users/me");
}

/** Auth entry point for the Telegram Mini App (see components/telegram/telegram-webapp-gate.tsx).
 * Not a react-query mutation like the others below — it runs once, imperatively, from an effect
 * before the rest of the app renders, so there's no UI action to attach a mutation hook to. */
export async function telegramWebAppLogin(initData: string): Promise<User> {
  const session = await api.post<SessionResponse>(
    "/auth/telegram-webapp",
    { init_data: initData },
    { skipAuth: true }
  );
  // Set before fetching the profile so that request carries the new bearer token.
  useAuthStore.getState().setTokens(session.access_token, session.csrf_token);
  const user = await fetchMe();
  useAuthStore.getState().setSession(session.access_token, session.csrf_token, user);
  return user;
}

export function useCurrentUser() {
  const accessToken = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ["me"],
    queryFn: fetchMe,
    enabled: !!accessToken,
    retry: false,
  });
}

export function useLogout() {
  const clear = useAuthStore((s) => s.clear);
  const queryClient = useQueryClient();
  return () => {
    const { csrfToken } = useAuthStore.getState();
    if (csrfToken) {
      // The refresh token itself is in an httpOnly cookie, so the request carries no body — the
      // server reads the cookie and revokes the whole family (D-14). CSRF applies here too: a
      // forced logout is a small attack, but the check is free.
      fetch("/api/v1/auth/logout", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
      }).catch(() => {
        // Best-effort revocation; clearing local state is what the user actually experiences.
      });
    }
    clear();
    queryClient.clear();
  };
}

export function useUpdateProfile() {
  const setUser = useAuthStore((s) => s.setUser);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: Record<string, unknown>) => api.patch<User>("/users/me", input),
    onSuccess: (user) => {
      setUser(user);
      queryClient.setQueryData(["me"], user);
    },
  });
}
