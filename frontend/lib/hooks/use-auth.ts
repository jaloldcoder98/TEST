"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api-client";
import { useAuthStore } from "@/lib/stores/auth-store";
import type { Language, TokenResponse, User } from "@/lib/types";

interface RegisterInput {
  username: string;
  password: string;
  email?: string;
  first_name?: string;
  last_name?: string;
  language: Language;
}

interface LoginInput {
  username: string;
  password: string;
}

async function fetchMe(): Promise<User> {
  return api.get<User>("/users/me");
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

export function useRegister() {
  const setSession = useAuthStore((s) => s.setSession);
  return useMutation({
    mutationFn: async (input: RegisterInput) => {
      const tokens = await api.post<TokenResponse>("/auth/register", input, { skipAuth: true });
      useAuthStore.setState({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
      const user = await fetchMe();
      setSession(tokens.access_token, tokens.refresh_token, user);
      return user;
    },
  });
}

export function useLogin() {
  const setSession = useAuthStore((s) => s.setSession);
  return useMutation({
    mutationFn: async (input: LoginInput) => {
      const tokens = await api.post<TokenResponse>("/auth/login", input, { skipAuth: true });
      useAuthStore.setState({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
      const user = await fetchMe();
      setSession(tokens.access_token, tokens.refresh_token, user);
      return user;
    },
  });
}

export function useLogout() {
  const clear = useAuthStore((s) => s.clear);
  const queryClient = useQueryClient();
  return () => {
    const refreshToken = useAuthStore.getState().refreshToken;
    if (refreshToken) {
      api.post("/auth/logout", { refresh_token: refreshToken }).catch(() => {
        // Best-effort server-side revocation — clearing local state is what actually matters
        // for the user, so a network failure here shouldn't block logout.
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
