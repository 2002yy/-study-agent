// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusDot } from "./StatusDot";

describe("StatusDot", () => {
  it("defaults to neutral tone", () => {
    const { container } = render(<StatusDot />);

    expect(container.querySelector(".status-dot")).toHaveClass("neutral");
  });

  it.each(["good", "warn", "neutral", "bad"] as const)(
    "applies the %s tone class",
    (tone) => {
      const { container } = render(<StatusDot tone={tone} />);

      expect(container.querySelector(".status-dot")).toHaveClass(tone);
    },
  );
});
