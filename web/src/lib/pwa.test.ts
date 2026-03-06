import { describe, expect, it, vi } from "vitest";
import { registerPwaServiceWorker } from "./pwa";

describe("registerPwaServiceWorker", () => {
  it("returns null when serviceWorker is unavailable", async () => {
    const originalNavigator = globalThis.navigator;
    Object.defineProperty(globalThis, "navigator", {
      configurable: true,
      value: {},
    });
    await expect(registerPwaServiceWorker(false)).resolves.toBeNull();
    Object.defineProperty(globalThis, "navigator", { configurable: true, value: originalNavigator });
  });

  it("registers service worker in production", async () => {
    const register = vi.fn().mockResolvedValue({ scope: "/" });
    const originalNavigator = globalThis.navigator;
    Object.defineProperty(globalThis, "navigator", {
      configurable: true,
      value: { serviceWorker: { register } },
    });
    await registerPwaServiceWorker(false);
    expect(register).toHaveBeenCalledWith("/sw.js");
    Object.defineProperty(globalThis, "navigator", { configurable: true, value: originalNavigator });
  });

  it("does not register in dev mode", async () => {
    const register = vi.fn().mockResolvedValue({ scope: "/" });
    const originalNavigator = globalThis.navigator;
    Object.defineProperty(globalThis, "navigator", {
      configurable: true,
      value: { serviceWorker: { register } },
    });
    await expect(registerPwaServiceWorker(true)).resolves.toBeNull();
    expect(register).not.toHaveBeenCalled();
    Object.defineProperty(globalThis, "navigator", { configurable: true, value: originalNavigator });
  });
});
