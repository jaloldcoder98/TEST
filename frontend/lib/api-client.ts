"use client";

/* TODO(webapp-first): TZ §6 — when a refresh fails, refreshAccessToken() clears the session and the guard bounces
 * the user to /login. Inside Telegram there is no login to do: re-authenticate silently from
 * Telegram.WebApp.initData instead, and only fall through to /login in a plain browser.
 *
 * TZ §20 — every request here is JSON. Camera uploads need a multipart path (no Content-Type
 * header, FormData body) for POST /nutrition/analyze-image.
 * See docs/WEBAPP_FIRST_AUDIT.md for the full plan.
 */

import { useAuthStore } from "@/lib/stores/auth-store";
import type { ApiErrorBody, TokenResponse } from "@/lib/types";

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

async function refreshAccessToken(): Promise<string | null> {
  const { refreshToken, setTokens, user, setSession, clear } = useAuthStore.getState();
  if (!refreshToken) return null;

  // Coalesce concurrent 401s into a single refresh call instead of racing multiple rotations
  // against the single-use refresh token (app/core/security.py rotates + revokes on use).
  if (!refreshPromise) {
    refreshPromise = fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
      .then(async (res) => {
        if (!res.ok) throw new Error("refresh failed");
        const data: TokenResponse = await res.json();
        if (user) setSession(data.access_token, data.refresh_token, user);
        else setTokens(data.access_token, data.refresh_token);
        return data.access_token;
      })
      .catch(() => {
        clear();
        return null;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
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
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401 && !skipAuth && !isRetry) {
    const newToken = await refreshAccessToken();
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
