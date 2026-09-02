import { beforeEach, describe, expect, it } from "vitest";

import { useAuthStore } from "@/lib/stores/auth-store";
import type { User } from "@/lib/types";

const fakeUser: User = {
  id: "11111111-1111-1111-1111-111111111111",
  username: "lifter",
  email: null,
  first_name: null,
  last_name: null,
  language: "en",
  is_admin: false,
  profile: null,
} as unknown as User;

describe("useAuthStore", () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: null, refreshToken: null, user: null });
  });

  it("starts logged out", () => {
    const state = useAuthStore.getState();
    expect(state.accessToken).toBeNull();
    expect(state.refreshToken).toBeNull();
    expect(state.user).toBeNull();
  });

  it("setSession stores tokens and the user together", () => {
    useAuthStore.getState().setSession("access-1", "refresh-1", fakeUser);
    const state = useAuthStore.getState();
    expect(state.accessToken).toBe("access-1");
    expect(state.refreshToken).toBe("refresh-1");
    expect(state.user).toEqual(fakeUser);
  });

  it("setTokens rotates tokens without touching the stored user", () => {
    useAuthStore.getState().setSession("access-1", "refresh-1", fakeUser);
    useAuthStore.getState().setTokens("access-2", "refresh-2");
    const state = useAuthStore.getState();
    expect(state.accessToken).toBe("access-2");
    expect(state.refreshToken).toBe("refresh-2");
    expect(state.user).toEqual(fakeUser); // unchanged
  });

  it("setUser updates only the user", () => {
    useAuthStore.getState().setSession("access-1", "refresh-1", fakeUser);
    const updated = { ...fakeUser, username: "renamed" };
    useAuthStore.getState().setUser(updated);
    const state = useAuthStore.getState();
    expect(state.user?.username).toBe("renamed");
    expect(state.accessToken).toBe("access-1"); // unchanged
  });

  it("clear logs the user out entirely", () => {
    useAuthStore.getState().setSession("access-1", "refresh-1", fakeUser);
    useAuthStore.getState().clear();
    const state = useAuthStore.getState();
    expect(state.accessToken).toBeNull();
    expect(state.refreshToken).toBeNull();
    expect(state.user).toBeNull();
  });
});
