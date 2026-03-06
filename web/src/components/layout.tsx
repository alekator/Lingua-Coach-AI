import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { api } from "../api/client";
import { t, uiLocaleFromNativeLang } from "../lib/i18n";
import { useAppStore } from "../store/app-store";
import { WorkspaceSwitcher } from "./workspace-switcher";

const navSections = [
  {
    title: "Today",
    links: [
      ["/app", "nav_dashboard", "🏠"],
      ["/app/session", "nav_session", "🧭"],
    ],
  },
  {
    title: "Practice",
    links: [
      ["/app/chat", "nav_chat", "💬"],
      ["/app/voice", "nav_voice", "🎙️"],
      ["/app/translate", "nav_translate", "🌐"],
      ["/app/vocab", "nav_vocab", "📚"],
      ["/app/exercises", "nav_exercises", "🧪"],
      ["/app/scenarios", "nav_scenarios", "🎭"],
      ["/app/grammar", "nav_grammar", "✍️"],
      ["/app/homework", "nav_homework", "✅"],
    ],
  },
  {
    title: "Manage",
    links: [["/app/profile", "nav_profile", "⚙️"]],
  },
] as const;

function resolveActiveNavLabel(pathname: string): string | null {
  for (const section of navSections) {
    for (const [to, labelKey] of section.links) {
      if (to === "/app" ? pathname === to : pathname.startsWith(to)) {
        return labelKey;
      }
    }
  }
  return null;
}

export function AppLayout() {
  const locale = uiLocaleFromNativeLang(useAppStore((s) => s.activeWorkspaceNativeLang));
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const location = useLocation();
  const keyStatus = useQuery({
    queryKey: ["openai-key-status-banner"],
    queryFn: api.openaiKeyStatus,
    retry: false,
    staleTime: 60_000,
    refetchInterval: 120_000,
  });
  const keyProbe = useQuery({
    queryKey: ["openai-key-probe-banner"],
    queryFn: api.debugOpenai,
    enabled: keyStatus.data?.configured === true,
    retry: false,
    staleTime: 5 * 60_000,
  });
  const showMissingKey = keyStatus.isSuccess && !keyStatus.data.configured;
  const showInvalidKey = keyStatus.data?.configured && keyProbe.isError;
  const showStatusUnknown = keyStatus.isError;
  const activeNavLabel = resolveActiveNavLabel(location.pathname);

  return (
    <div className="app-layout">
      <aside id="app-sidebar" className={`app-sidebar ${mobileNavOpen ? "open" : ""}`}>
        <div className="sidebar-brand">
          <h1>{t(locale, "app_title")}</h1>
          <p>{t(locale, "app_tagline")}</p>
        </div>
        <WorkspaceSwitcher />
        <nav className="sidebar-nav" aria-label="Primary">
          {navSections.map((section) => (
            <section key={section.title} className="sidebar-section">
              <h2>{section.title}</h2>
              {section.links.map(([to, labelKey, icon]) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === "/app"}
                  className={({ isActive }) => `sidebar-link ${isActive ? "active" : ""}`}
                  onClick={() => setMobileNavOpen(false)}
                >
                  <span className="sidebar-link-icon" aria-hidden="true">
                    {icon}
                  </span>
                  <span>{t(locale, labelKey)}</span>
                </NavLink>
              ))}
            </section>
          ))}
        </nav>
      </aside>
      <div className={`mobile-backdrop ${mobileNavOpen ? "show" : ""}`} onClick={() => setMobileNavOpen(false)} />
      <div className="app-main">
        <header className="topbar">
          <div className="shell-header panel">
            <div className="shell-header-main">
              <button
                type="button"
                className="mobile-nav-toggle"
                onClick={() => setMobileNavOpen((prev) => !prev)}
                aria-expanded={mobileNavOpen}
                aria-controls="app-sidebar"
              >
                {mobileNavOpen ? "Close menu" : "Open menu"}
              </button>
              <div>
                <h2>{t(locale, "app_title")}</h2>
                <p>{activeNavLabel ? t(locale, activeNavLabel) : t(locale, "app_tagline")}</p>
              </div>
            </div>
            <Link to="/app/session" className="shell-header-cta">
              Continue session
            </Link>
          </div>
          <div className="topbar-alerts">
          {showMissingKey && (
            <article className="panel stack" aria-live="polite">
              <strong>OpenAI key is not configured.</strong>
              <p>App continues in lightweight mode. Add your key in profile to unlock full AI coaching quality.</p>
              <Link to="/app/profile">Open profile settings</Link>
            </article>
          )}
          {showInvalidKey && (
            <article className="panel stack" aria-live="polite">
              <strong>OpenAI check failed.</strong>
              <p>
                Your key may be invalid, expired, or quota-limited. App remains usable in lightweight mode until fixed.
              </p>
              <Link to="/app/profile">Review API key settings</Link>
            </article>
          )}
          {showStatusUnknown && (
            <article className="panel stack" aria-live="polite">
              <strong>Unable to check OpenAI key status.</strong>
              <p>App may run in lightweight mode while connection checks are unavailable.</p>
            </article>
          )}
          </div>
        </header>
        <main>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
