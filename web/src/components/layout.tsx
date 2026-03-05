import { Link, Outlet } from "react-router-dom";
import { WorkspaceSwitcher } from "./workspace-switcher";

const links = [
  ["/app", "Dashboard"],
  ["/app/session", "Daily Session"],
  ["/app/chat", "Coach Chat"],
  ["/app/voice", "Speaking"],
  ["/app/translate", "Translate"],
  ["/app/vocab", "Word Bank"],
  ["/app/exercises", "Drills"],
  ["/app/scenarios", "Roleplays"],
  ["/app/grammar", "Grammar"],
  ["/app/homework", "Homework"],
  ["/app/profile", "Profile"],
] as const;

export function AppLayout() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <h1>LinguaCoach AI</h1>
        <p>Plan - Practice - Feedback - Progress</p>
        <WorkspaceSwitcher />
        <nav>
          {links.map(([to, label]) => (
            <Link key={to} to={to}>
              {label}
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
