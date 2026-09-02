import { describe, expect, it } from "vitest";

import { cn } from "@/lib/utils";

describe("cn", () => {
  it("joins truthy class fragments", () => {
    expect(cn("a", "b", "c")).toBe("a b c");
  });

  it("drops falsy fragments", () => {
    expect(cn("a", false && "b", undefined, null, "c")).toBe("a c");
  });

  it("lets a later conflicting Tailwind class win (tailwind-merge)", () => {
    // twMerge resolves same-property conflicts by keeping the last one, which is exactly what
    // components like Card/Button rely on when a caller passes an overriding className.
    expect(cn("px-2 py-1", "px-4")).toBe("py-1 px-4");
  });

  it("supports conditional object syntax", () => {
    expect(cn("base", { active: true, hidden: false })).toBe("base active");
  });
});
