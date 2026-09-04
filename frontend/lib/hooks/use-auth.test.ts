import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { telegramWebAppLogin } from "@/lib/hooks/use-auth";
import { useAuthStore } from "@/lib/stores/auth-store";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

describe("telegramWebAppLogin", () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: null, csrfToken: null, user: null });
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("exchanges initData for tokens, fetches the profile, and stores the session", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse(200, { access_token: "tg-access", csrf_token: "tg-csrf" }))
      .mockResolvedValueOnce(jsonResponse(200, { id: "u1", username: "tg_123" }));

    const user = await telegramWebAppLogin("query_id=abc&user=%7B%7D&auth_date=1&hash=deadbeef");

    expect(user).toEqual({ id: "u1", username: "tg_123" });
    expect(useAuthStore.getState().accessToken).toBe("tg-access");
    expect(useAuthStore.getState().csrfToken).toBe("tg-csrf");
    // The refresh token is never in the response body — it arrives as an httpOnly cookie (D-13).
    expect(useAuthStore.getState().user).toEqual({ id: "u1", username: "tg_123" });

    const [authCall] = vi.mocked(fetch).mock.calls[0];
    expect(authCall).toBe("http://localhost:3000/api/v1/auth/telegram-webapp");
    // skipAuth: true means no stale Authorization header should have been sent, even though a
    // request could in principle race with one already in flight.
    const [, authInit] = vi.mocked(fetch).mock.calls[0];
    expect(authInit?.headers).not.toHaveProperty("Authorization");
  });

  it("propagates a rejected (e.g. invalid signature) init_data as a thrown error", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(401, { success: false, error: { code: "UNAUTHORIZED", message: "Invalid Telegram Web App init data signature" } })
    );

    await expect(telegramWebAppLogin("tampered")).rejects.toMatchObject({ code: "UNAUTHORIZED" });
    expect(useAuthStore.getState().accessToken).toBeNull();
  });
});
