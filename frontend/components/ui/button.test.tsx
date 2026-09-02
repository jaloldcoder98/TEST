import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Button } from "@/components/ui/button";

describe("Button", () => {
  it("renders its children and defaults to the primary variant", () => {
    render(<Button>Save workout</Button>);
    const btn = screen.getByRole("button", { name: "Save workout" });
    expect(btn).toBeInTheDocument();
    expect(btn.className).toContain("bg-primary");
  });

  it("applies the destructive variant's classes", () => {
    render(<Button variant="destructive">Delete</Button>);
    expect(screen.getByRole("button", { name: "Delete" }).className).toContain("bg-destructive");
  });

  it("is disabled and non-interactive when disabled is passed", () => {
    const onClick = vi.fn();
    render(
      <Button disabled onClick={onClick}>
        Locked
      </Button>
    );
    const btn = screen.getByRole("button", { name: "Locked" });
    expect(btn).toBeDisabled();
  });

  it("merges a caller-provided className without dropping the variant classes", () => {
    render(<Button className="w-full">Full width</Button>);
    const btn = screen.getByRole("button", { name: "Full width" });
    expect(btn.className).toContain("w-full");
    expect(btn.className).toContain("bg-primary");
  });
});
