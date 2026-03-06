import { describe, expect, it } from "vitest";
import { t, uiLocaleFromNativeLang } from "./i18n";

describe("i18n", () => {
  it("resolves locale from native language", () => {
    expect(uiLocaleFromNativeLang("ru")).toBe("ru");
    expect(uiLocaleFromNativeLang("ru-RU")).toBe("ru");
    expect(uiLocaleFromNativeLang("de")).toBe("en");
    expect(uiLocaleFromNativeLang(null)).toBe("en");
  });

  it("returns localized text with english fallback", () => {
    expect(t("ru", "onboarding_title")).toBe("Первый запуск");
    expect(t("en", "onboarding_title")).toBe("First Launch Setup");
    expect(t("ru", "unknown_key")).toBe("unknown_key");
  });
});

