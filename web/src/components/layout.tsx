import { useQuery } from "@tanstack/react-query";
import { Link, Outlet } from "react-router-dom";
import { api } from "../api/client";
import { t, uiLocaleFromNativeLang } from "../lib/i18n";
import { useAppStore } from "../store/app-store";
import { WorkspaceSwitcher } from "./workspace-switcher";

const links = [
  ["/app", "nav_dashboard"],
  ["/app/session", "nav_session"],
  ["/app/chat", "nav_chat"],
  ["/app/voice", "nav_voice"],
  ["/app/translate", "nav_translate"],
  ["/app/vocab", "nav_vocab"],
  ["/app/exercises", "nav_exercises"],
  ["/app/scenarios", "nav_scenarios"],
  ["/app/grammar", "nav_grammar"],
  ["/app/homework", "nav_homework"],
  ["/app/profile", "nav_profile"],
] as const;

export function AppLayout() {
  const locale = uiLocaleFromNativeLang(useAppStore((s) => s.activeWorkspaceNativeLang));
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

  return (
    <div className="app-shell">
      <header className="topbar">
        <h1>{t(locale, "app_title")}</h1>
        <p>{t(locale, "app_tagline")}</p>
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
        <WorkspaceSwitcher />
        <nav>
          {links.map(([to, labelKey]) => (
            <Link key={to} to={to}>
              {t(locale, labelKey)}
            </Link>
          ))}
        </nav>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
