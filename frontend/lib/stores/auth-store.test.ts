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
  role: "user",
  profile: null,
};

describe("useAuthStore", () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: null, csrfToken: null, user: null });
  });

  it("starts logged out", () => {
    const state = useAuthStore.getState();
    expect(state.accessToken).toBeNull();
    expect(state.csrfToken).toBeNull();
    expect(state.user).toBeNull();
  });

  it("setSession stores the access and CSRF tokens together with the user", () => {
    useAuthStore.getState().setSession("access-1", "csrf-1", fakeUser);
    const state = useAuthStore.getState();
    expect(state.accessToken).toBe("access-1");
    expect(state.csrfToken).toBe("csrf-1");
    expect(state.user).toEqual(fakeUser);
  });

  it("setTokens rotates the pair without touching the user", () => {
    useAuthStore.getState().setSession("access-1", "csrf-1", fakeUser);
    useAuthStore.getState().setTokens("access-2", "csrf-2");
    const state = useAuthStore.getState();
    expect(state.accessToken).toBe("access-2");
    expect(state.csrfToken).toBe("csrf-2");
    expect(state.user).toEqual(fakeUser);
  });

  it("clear wipes everything", () => {
    useAuthStore.getState().setSession("access-1", "csrf-1", fakeUser);
    useAuthStore.getState().clear();
    const state = useAuthStore.getState();
    expect(state.accessToken).toBeNull();
    expect(state.csrfToken).toBeNull();
    expect(state.user).toBeNull();
  });

  it("never holds a refresh token, and persists nothing", () => {
    // The two properties the whole session model rests on (docs/DECISIONS.md D-12, D-13): the
    // refresh token lives in an httpOnly cookie the page cannot read, and nothing about the
    // session survives in storage for an XSS bug to find.
    useAuthStore.getState().setSession("access-1", "csrf-1", fakeUser);
    expect(Object.keys(useAuthStore.getState())).not.toContain("refreshToken");
    expect(window.localStorage.length).toBe(0);
  });
});
