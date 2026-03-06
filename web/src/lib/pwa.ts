export async function registerPwaServiceWorker(isDev = import.meta.env.DEV): Promise<ServiceWorkerRegistration | null> {
  if (typeof window === "undefined" || !("serviceWorker" in navigator)) {
    return null;
  }
  if (isDev) {
    return null;
  }
  return navigator.serviceWorker.register("/sw.js");
}
