import { Link, Outlet } from "react-router-dom";
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
  return (
    <div className="app-shell">
      <header className="topbar">
        <h1>{t(locale, "app_title")}</h1>
        <p>{t(locale, "app_tagline")}</p>
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
