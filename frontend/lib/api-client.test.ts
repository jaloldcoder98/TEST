import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, ApiError } from "@/lib/api-client";
import { useAuthStore } from "@/lib/stores/auth-store";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

describe("api client", () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: "old-access", refreshToken: "old-refresh", user: null });
    vi.stubGlobal("fetch", vi.fn());
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

  it("on a 401, refreshes the access token once and retries the original request", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse(401, { success: false, error: { code: "UNAUTHORIZED", message: "Expired" } }))
      .mockResolvedValueOnce(jsonResponse(200, { access_token: "new-access", refresh_token: "new-refresh" }))
      .mockResolvedValueOnce(jsonResponse(200, { items: [] }));

    const result = await api.get<{ items: unknown[] }>("/workouts");

    expect(result).toEqual({ items: [] });
    expect(fetch).toHaveBeenCalledTimes(3);
    expect(useAuthStore.getState().accessToken).toBe("new-access");

    // The retried request used the newly rotated token, not the stale one.
    const retryCall = vi.mocked(fetch).mock.calls[2];
    expect(retryCall[1]?.headers).toMatchObject({ Authorization: "Bearer new-access" });
  });

  it("logs the user out when the refresh token itself is rejected", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse(401, { success: false, error: { code: "UNAUTHORIZED", message: "Expired" } }))
      .mockResolvedValueOnce(jsonResponse(401, { success: false, error: { code: "UNAUTHORIZED", message: "Bad refresh" } }));

    await expect(api.get("/workouts")).rejects.toBeInstanceOf(ApiError);
    expect(useAuthStore.getState().accessToken).toBeNull();
    expect(useAuthStore.getState().refreshToken).toBeNull();
  });
});
