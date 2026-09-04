import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, ApiError } from "@/lib/api-client";
import { useAuthStore } from "@/lib/stores/auth-store";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

describe("api client", () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: "old-access", csrfToken: "old-csrf", user: null });
    vi.stubGlobal("fetch", vi.fn());
    // No Telegram SDK by default: these tests exercise the cookie-refresh path. The silent
    // re-auth fallback gets its own test below, where the SDK is stubbed in.
    vi.stubGlobal("Telegram", undefined);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns parsed JSON on success", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(200, { success: true, id: "abc" }));

    const result = await api.get<{ success: boolean; id: string }>("/workouts/abc");

    expect(result).toEqual({ success: true, id: "abc" });
    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(init?.headers).toMatchObject({ Authorization: "Bearer old-access" });
  });

  it("throws an ApiError carrying the backend's error code, message, and status", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(404, { success: false, error: { code: "WORKOUT_NOT_FOUND", message: "Workout not found" } })
    );

    await expect(api.get("/workouts/missing")).rejects.toMatchObject({
      code: "WORKOUT_NOT_FOUND",
      message: "Workout not found",
      status: 404,
    });
  });

  it("the thrown error is an actual ApiError instance", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(500, { success: false, error: { code: "INTERNAL_ERROR", message: "Boom" } })
    );

    await expect(api.get("/workouts/missing")).rejects.toBeInstanceOf(ApiError);
  });

  it("on a 401, refreshes with the cookie once and retries the original request", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse(401, { success: false, error: { code: "UNAUTHORIZED", message: "Expired" } }))
      .mockResolvedValueOnce(jsonResponse(200, { access_token: "new-access", csrf_token: "new-csrf" }))
      .mockResolvedValueOnce(jsonResponse(200, { items: [] }));

    const result = await api.get<{ items: unknown[] }>("/workouts");

    expect(result).toEqual({ items: [] });
    expect(fetch).toHaveBeenCalledTimes(3);
    expect(useAuthStore.getState().accessToken).toBe("new-access");

    // The retried request used the newly rotated token, not the stale one.
    const retryCall = vi.mocked(fetch).mock.calls[2];
    expect(retryCall[1]?.headers).toMatchObject({ Authorization: "Bearer new-access" });

    // The refresh call carried the double-submit CSRF header and the cookie (D-19).
    const refreshCall = vi.mocked(fetch).mock.calls[1];
    expect(refreshCall[1]?.headers).toMatchObject({ "X-CSRF-Token": "old-csrf" });
    expect(refreshCall[1]?.credentials).toBe("include");
  });

  it("falls back to silent re-auth with initData when the cookie refresh fails", async () => {
    // Invariant 16: on Telegram Web/Safari the cookie may never have been stored at all, so a
    // failed refresh must not mean a signed-out user while Telegram can still vouch for them.
    vi.stubGlobal("Telegram", { WebApp: { initData: "signed-init-data" } });
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse(401, { success: false, error: { code: "UNAUTHORIZED", message: "Expired" } }))
      .mockResolvedValueOnce(jsonResponse(401, { success: false, error: { code: "UNAUTHORIZED", message: "No session" } }))
      .mockResolvedValueOnce(jsonResponse(200, { access_token: "reauth-access", csrf_token: "reauth-csrf" }))
      .mockResolvedValueOnce(jsonResponse(200, { items: [] }));

    const result = await api.get<{ items: unknown[] }>("/workouts");

    expect(result).toEqual({ items: [] });
    expect(useAuthStore.getState().accessToken).toBe("reauth-access");
    const reauthCall = vi.mocked(fetch).mock.calls[2];
    expect(String(reauthCall[0])).toContain("/auth/telegram-webapp");
    expect(reauthCall[1]?.body).toBe(JSON.stringify({ init_data: "signed-init-data" }));
  });

  it("only signs the user out when both recovery paths fail", async () => {
    // Outside Telegram there is no initData to fall back on, so a rejected cookie really is the
    // end of the session.
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse(401, { success: false, error: { code: "UNAUTHORIZED", message: "Expired" } }))
      .mockResolvedValueOnce(jsonResponse(401, { success: false, error: { code: "UNAUTHORIZED", message: "Bad refresh" } }));

    await expect(api.get("/workouts")).rejects.toBeInstanceOf(ApiError);
    expect(useAuthStore.getState().accessToken).toBeNull();
    expect(useAuthStore.getState().csrfToken).toBeNull();
  });
});
