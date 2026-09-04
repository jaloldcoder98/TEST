"use client";

import { useAuthStore } from "@/lib/stores/auth-store";
import type { ApiErrorBody, SessionResponse } from "@/lib/types";

// Relative by default so the browser always calls the site's own origin — next.config.mjs
// proxies /api/v1/* to the backend server-side. This is what makes the app work from a single
// public HTTPS URL (e.g. an ngrok tunnel for Telegram Mini App testing) without also exposing
// the backend separately. Set NEXT_PUBLIC_API_URL to override (e.g. pointing straight at a
// backend running outside Docker during native local dev — see README).
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";

export class ApiError extends Error {
  code: string;
  status: number;

  constructor(code: string, message: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

let refreshPromise: Promise<string | null> | null = null;

/**
 * Recover a session after a 401, in two steps (docs/DECISIONS.md D-15, invariant 16).
 *
 * First try the refresh cookie. It may simply not be there — Telegram Web runs the Mini App in a
 * cross-site iframe where Safari blocks the cookie outright, and iOS WKWebView is documented to
 * drop stored data unpredictably. That is a normal condition, not an error, which is why the
 * second step exists: ask Telegram for fresh `initData` and start a new session with it. Only if
 * *both* fail is the user really signed out.
 *
 * Concurrent 401s are coalesced into one attempt: the refresh token is single-use and rotating
 * it twice in parallel would trip the server's reuse detection and revoke the whole family.
 */
async function recoverSession(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const { csrfToken, setTokens, clear } = useAuthStore.getState();

    if (csrfToken) {
      try {
        const res = await fetch(`${API_URL}/auth/refresh`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
        });
        if (res.ok) {
          const data: SessionResponse = await res.json();
          setTokens(data.access_token, data.csrf_token);
          return data.access_token;
        }
      } catch {
        // Network failure — fall through to re-authentication rather than giving up.
      }
    }

    const initData = typeof window !== "undefined" ? window.Telegram?.WebApp?.initData : undefined;
    if (initData) {
      try {
        const res = await fetch(`${API_URL}/auth/telegram-webapp`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ init_data: initData }),
        });
        if (res.ok) {
          const data: SessionResponse = await res.json();
          setTokens(data.access_token, data.csrf_token);
          return data.access_token;
        }
      } catch {
        // Same again: nothing left to try, fall through to clearing state.
      }
    }

    clear();
    return null;
  })().finally(() => {
    refreshPromise = null;
  });

  return refreshPromise;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined | null>;
  skipAuth?: boolean;
}

function buildUrl(path: string, params?: RequestOptions["params"]) {
  // API_URL is relative by default (see above), and `new URL()` requires an absolute string
  // unless given a base — window.location.origin covers both a real browser and the jsdom test
  // environment (which stubs one too), and this only touches the *first* argument's parsing, not
  // where the request actually goes: fetch() below resolves the returned string against the page
  // origin exactly like any relative URL would.
  const url = new URL(`${API_URL}${path}`, window.location.origin);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

async function request<T>(path: string, options: RequestOptions = {}, isRetry = false): Promise<T> {
  const { method = "GET", body, params, skipAuth = false } = options;
  const token = useAuthStore.getState().accessToken;

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (!skipAuth && token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(buildUrl(path, params), {
    method,
    headers,
    // Ordinary requests authenticate with the bearer header, but the cookie has to ride along so
    // /auth/refresh can find it — and sending it costs nothing elsewhere, since no other endpoint
    // reads it (D-19).
    credentials: "include",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401 && !skipAuth && !isRetry) {
    const newToken = await recoverSession();
    if (newToken) return request<T>(path, options, true);
  }

  if (!res.ok) {
    let parsed: ApiErrorBody | null = null;
    try {
      parsed = await res.json();
    } catch {
      // non-JSON error body (e.g. a proxy/network error page) — fall through to generic message
    }
    throw new ApiError(
      parsed?.error?.code ?? "UNKNOWN_ERROR",
      parsed?.error?.message ?? `Request failed with status ${res.status}`,
      res.status
    );
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  get: <T>(path: string, params?: RequestOptions["params"]) => request<T>(path, { method: "GET", params }),
  post: <T>(path: string, body?: unknown, options?: Partial<RequestOptions>) =>
    request<T>(path, { method: "POST", body, ...options }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
