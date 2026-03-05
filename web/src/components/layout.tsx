import { Link, Outlet } from "react-router-dom";

const links = [
  ["/app", "Dashboard"],
  ["/app/chat", "Chat"],
  ["/app/voice", "Voice"],
  ["/app/translate", "Translate"],
  ["/app/vocab", "Vocab"],
  ["/app/exercises", "Exercises"],
  ["/app/scenarios", "Scenarios"],
  ["/app/grammar", "Grammar"],
  ["/app/homework", "Homework"],
  ["/app/profile", "Progress"],
] as const;

export function AppLayout() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <h1>LinguaCoach AI</h1>
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
