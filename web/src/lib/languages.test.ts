import { describe, expect, it } from "vitest";
import { languageLabelByCode, normalizeLanguageCode } from "./languages";

describe("languages helpers", () => {
  it("normalizes language code", () => {
    expect(normalizeLanguageCode(" EN ")).toBe("en");
  });

  it("returns friendly label for known code", () => {
    expect(languageLabelByCode("de")).toContain("German");
  });

  it("falls back to normalized code for unknown language", () => {
    expect(languageLabelByCode("xx")).toBe("xx");
  });
});

