import { useQuery } from "@tanstack/react-query";
import { FormEvent, useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { api } from "../api/client";
import { t, uiLocaleFromNativeLang } from "../lib/i18n";
import { getErrorMessage } from "../lib/errors";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";
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

type KeyIssue = {
  title: string;
  message: string;
};

type RuntimeModule = "llm" | "asr" | "tts";

function classifyOpenAIProbeError(error: unknown): KeyIssue {
  const status = typeof error === "object" && error !== null && "status" in error ? Number(error.status) : undefined;
  const message =
    typeof error === "object" && error !== null && "message" in error ? String(error.message).toLowerCase() : "";

  const isQuota =
    status === 429 ||
    message.includes("insufficient_quota") ||
    message.includes("quota") ||
    message.includes("billing") ||
    message.includes("payment");
  if (isQuota) {
    return {
      title: "OpenAI key saved, but quota/billing is unavailable.",
      message: "AI requests are currently limited. Add billing/quota and app will switch from lightweight mode.",
    };
  }

  const isInvalid =
    status === 401 ||
    message.includes("invalid_api_key") ||
    message.includes("incorrect api key") ||
    message.includes("invalid api key") ||
    message.includes("authentication");
  if (isInvalid) {
    return {
      title: "OpenAI key appears invalid.",
      message: "Check key value and permissions. App stays in lightweight mode until key verification succeeds.",
    };
  }

  const isNetwork =
    status === 502 ||
    status === 503 ||
    status === 504 ||
    message.includes("network") ||
    message.includes("timeout") ||
    message.includes("connection");
  if (isNetwork) {
    return {
      title: "OpenAI network/API is unavailable.",
      message: "Service check failed due to connectivity or upstream issues. App continues in lightweight mode.",
    };
  }

  return {
    title: "OpenAI key check failed.",
    message: "App remains usable in lightweight mode until verification succeeds.",
  };
}

export function AppLayout() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const locale = uiLocaleFromNativeLang(useAppStore((s) => s.activeWorkspaceNativeLang));
  const theme = useAppStore((s) => s.theme);
  const setTheme = useAppStore((s) => s.setTheme);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [llmProviderDraft, setLlmProviderDraft] = useState<"openai" | "local">("openai");
  const [asrProviderDraft, setAsrProviderDraft] = useState<"openai" | "local">("openai");
  const [ttsProviderDraft, setTtsProviderDraft] = useState<"openai" | "local">("openai");
  const [providerBusy, setProviderBusy] = useState<RuntimeModule | null>(null);
  const [apiKeyDraft, setApiKeyDraft] = useState("");
  const [apiKeyBusy, setApiKeyBusy] = useState(false);
  const [dailyTokenCap, setDailyTokenCap] = useState("12000");
  const [weeklyTokenCap, setWeeklyTokenCap] = useState("60000");
  const [warningThreshold, setWarningThreshold] = useState("0.8");
  const [budgetSaving, setBudgetSaving] = useState(false);
  const location = useLocation();
  const pushToast = useToastStore((s) => s.push);
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
  const aiRuntime = useQuery({
    queryKey: ["ai-runtime-status-banner"],
    queryFn: () => api.aiRuntimeStatus(false),
    retry: false,
    staleTime: 60_000,
  });
  const usageBudget = useQuery({
    queryKey: ["usage-budget-sidebar", userId],
    queryFn: () => api.usageBudgetStatus(userId),
  });
  const llmIsLocal = aiRuntime.data?.llm_provider === "local";
  const showMissingKey = keyStatus.isSuccess && !keyStatus.data.configured && !llmIsLocal;
  const keyIssue =
    keyStatus.data?.configured && keyProbe.isError && !llmIsLocal ? classifyOpenAIProbeError(keyProbe.error) : null;
  const showInvalidKey = Boolean(keyIssue);
  const showStatusUnknown = keyStatus.isError;
  const showLocalRuntimeIssue =
    llmIsLocal &&
    aiRuntime.isSuccess &&
    (aiRuntime.data.llm.status !== "ok" || aiRuntime.data.asr.status === "error" || aiRuntime.data.tts.status === "error");
  const activeNavLabel = resolveActiveNavLabel(location.pathname);
  const showProfileRuntimeStrip = location.pathname.startsWith("/app/profile");
  const keyProbeIssue =
    keyStatus.data?.configured && keyProbe.isError && !llmIsLocal ? classifyOpenAIProbeError(keyProbe.error) : null;
  const keyLampTone: "ok" | "warn" | "bad" =
    keyStatus.isError || !keyStatus.data?.configured ? "bad" : keyProbeIssue ? "warn" : "ok";
  const keyLampHint = keyStatus.isError
    ? "Unable to check key status right now."
    : !keyStatus.data?.configured
      ? "OpenAI key is not configured."
      : keyProbeIssue
        ? `${keyProbeIssue.title} ${keyProbeIssue.message}`
        : `Status: configured ${keyStatus.data.masked ? `(${keyStatus.data.masked})` : ""}`;

  useEffect(() => {
    if (!aiRuntime.data) return;
    setLlmProviderDraft(aiRuntime.data.llm_provider);
    setAsrProviderDraft(aiRuntime.data.asr_provider);
    setTtsProviderDraft(aiRuntime.data.tts_provider);
  }, [aiRuntime.data]);

  useEffect(() => {
    if (!usageBudget.data) return;
    setDailyTokenCap(String(usageBudget.data.daily_token_cap));
    setWeeklyTokenCap(String(usageBudget.data.weekly_token_cap));
    setWarningThreshold(String(usageBudget.data.warning_threshold));
  }, [usageBudget.data]);

  async function onChangeProvider(module: RuntimeModule) {
    if (providerBusy) return;
    const nextProvider =
      module === "llm"
        ? llmProviderDraft === "openai"
          ? "local"
          : "openai"
        : module === "asr"
          ? asrProviderDraft === "openai"
            ? "local"
            : "openai"
          : ttsProviderDraft === "openai"
            ? "local"
            : "openai";
    const prev = {
      llm: llmProviderDraft,
      asr: asrProviderDraft,
      tts: ttsProviderDraft,
    };
    if (module === "llm") setLlmProviderDraft(nextProvider);
    if (module === "asr") setAsrProviderDraft(nextProvider);
    if (module === "tts") setTtsProviderDraft(nextProvider);
    setProviderBusy(module);
    try {
      await api.aiRuntimeSet({
        llm_provider: module === "llm" ? nextProvider : llmProviderDraft,
        asr_provider: module === "asr" ? nextProvider : asrProviderDraft,
        tts_provider: module === "tts" ? nextProvider : ttsProviderDraft,
      });
      await aiRuntime.refetch();
    } catch (err) {
      setLlmProviderDraft(prev.llm);
      setAsrProviderDraft(prev.asr);
      setTtsProviderDraft(prev.tts);
      pushToast("error", getErrorMessage(err));
    } finally {
      setProviderBusy(null);
    }
  }

  async function onSaveBudget(event: FormEvent) {
    event.preventDefault();
    setBudgetSaving(true);
    try {
      await api.usageBudgetSet({
        user_id: userId,
        daily_token_cap: Number(dailyTokenCap),
        weekly_token_cap: Number(weeklyTokenCap),
        warning_threshold: Number(warningThreshold),
      });
      await usageBudget.refetch();
      pushToast("success", "Usage limits updated");
    } catch (err) {
      pushToast("error", getErrorMessage(err));
    } finally {
      setBudgetSaving(false);
    }
  }

  async function onSaveApiKeySidebar() {
    const candidate = apiKeyDraft.trim();
    if (!candidate) return;
    setApiKeyBusy(true);
    try {
      await api.openaiKeySet({ api_key: candidate });
      await keyStatus.refetch();
      await keyProbe.refetch();
      setApiKeyDraft("");
      pushToast("success", "OpenAI key saved");
    } catch (err) {
      pushToast("error", getErrorMessage(err));
    } finally {
      setApiKeyBusy(false);
    }
  }

  return (
    <div className="app-layout">
      <aside id="app-sidebar" className={`app-sidebar ${mobileNavOpen ? "open" : ""}`}>
        <div className="sidebar-brand">
          <div className="sidebar-brand-title">
            <h1>{t(locale, "app_title")}</h1>
            <button
              type="button"
              className="theme-toggle"
              aria-label={theme === "dark-elegant" ? "Switch to light theme" : "Switch to dark elegant theme"}
              title={theme === "dark-elegant" ? "Switch to light theme" : "Switch to dark elegant theme"}
              onClick={() => setTheme(theme === "dark-elegant" ? "light" : "dark-elegant")}
            >
              {theme === "dark-elegant" ? (
                <svg className="theme-icon" viewBox="0 0 24 24" aria-hidden="true">
                  <circle cx="12" cy="12" r="4.2" />
                  <path d="M12 1.8v2.6M12 19.6v2.6M4.2 12H1.6M22.4 12h-2.6M5.7 5.7 3.8 3.8M20.2 20.2l-1.9-1.9M18.3 5.7l1.9-1.9M3.8 20.2l1.9-1.9" />
                </svg>
              ) : (
                <svg className="theme-icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M14.7 2.2a9.6 9.6 0 1 0 7.1 16.9 8.3 8.3 0 0 1-10.5-10.6 8.7 8.7 0 0 1 3.4-6.3Z" />
                </svg>
              )}
            </button>
          </div>
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
        {showProfileRuntimeStrip && (
          <article className="sidebar-key-widget">
            <div className="sidebar-key-head">
              <h3>OpenAI API Key</h3>
              <span className={`key-lamp ${keyLampTone}`} title={keyLampHint} aria-label={keyLampHint} />
            </div>
            <label>
              Key
              <input
                id="openai-key-input"
                aria-label="OpenAI API key (Sidebar)"
                type="password"
                placeholder="sk-..."
                value={apiKeyDraft}
                onChange={(e) => setApiKeyDraft(e.target.value)}
              />
            </label>
            <div className="sidebar-key-actions">
              <button type="button" onClick={onSaveApiKeySidebar} disabled={apiKeyBusy || !apiKeyDraft.trim()}>
                {apiKeyBusy ? "Saving..." : "Save key"}
              </button>
              <button type="button" onClick={() => void keyStatus.refetch()} disabled={keyStatus.isPending || apiKeyBusy}>
                Refresh status
              </button>
            </div>
          </article>
        )}
        {showProfileRuntimeStrip && (
          <article className="sidebar-budget-widget" aria-live="polite">
            <h3>AI Usage Budget</h3>
            {usageBudget.isPending && <p className="sidebar-budget-note">Loading...</p>}
            {usageBudget.isError && <p className="sidebar-budget-note">Failed to load budget.</p>}
            {usageBudget.isSuccess && (
              <>
                <table className="sidebar-budget-table">
                  <thead>
                    <tr>
                      <th>save</th>
                      <th>Today</th>
                      <th>Week</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>used</td>
                      <td>{usageBudget.data.daily_used_tokens}</td>
                      <td>{usageBudget.data.weekly_used_tokens}</td>
                    </tr>
                    <tr>
                      <td>limit</td>
                      <td>{usageBudget.data.daily_token_cap}</td>
                      <td>{usageBudget.data.weekly_token_cap}</td>
                    </tr>
                    <tr>
                      <td>usage</td>
                      <td>
                        {usageBudget.data.daily_token_cap > 0
                          ? Math.round((usageBudget.data.daily_used_tokens / usageBudget.data.daily_token_cap) * 100)
                          : 0}
                        %
                      </td>
                      <td>
                        {usageBudget.data.weekly_token_cap > 0
                          ? Math.round((usageBudget.data.weekly_used_tokens / usageBudget.data.weekly_token_cap) * 100)
                          : 0}
                        %
                      </td>
                    </tr>
                  </tbody>
                </table>
                <form className="sidebar-budget-form" onSubmit={onSaveBudget}>
                  <label>
                    Daily
                    <input type="number" min={0} value={dailyTokenCap} onChange={(e) => setDailyTokenCap(e.target.value)} />
                  </label>
                  <label>
                    Weekly
                    <input type="number" min={0} value={weeklyTokenCap} onChange={(e) => setWeeklyTokenCap(e.target.value)} />
                  </label>
                  <label>
                    Warn
                    <input
                      type="number"
                      min={0.5}
                      max={0.95}
                      step={0.05}
                      value={warningThreshold}
                      onChange={(e) => setWarningThreshold(e.target.value)}
                    />
                  </label>
                  <button type="submit" disabled={budgetSaving}>
                    {budgetSaving ? "Saving..." : "Save"}
                  </button>
                </form>
              </>
            )}
          </article>
        )}
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
              <div className="shell-header-title">
                <h2>{t(locale, "app_title")}</h2>
                <p>{activeNavLabel ? t(locale, activeNavLabel) : t(locale, "app_tagline")}</p>
              </div>
            </div>
            {showProfileRuntimeStrip && aiRuntime.data && (
              <div className="header-runtime-strip">
                <button
                  type="button"
                  className="header-runtime-entity"
                  onClick={() => void onChangeProvider("llm")}
                  disabled={providerBusy !== null}
                  aria-label="Toggle LLM provider"
                >
                  <span>LLM</span>
                  <span className={`runtime-provider-word ${llmProviderDraft}`}>
                    {providerBusy === "llm" ? "..." : llmProviderDraft.toUpperCase()}
                  </span>
                </button>
                <button
                  type="button"
                  className="header-runtime-entity"
                  onClick={() => void onChangeProvider("asr")}
                  disabled={providerBusy !== null}
                  aria-label="Toggle ASR provider"
                >
                  <span>ASR</span>
                  <span className={`runtime-provider-word ${asrProviderDraft}`}>
                    {providerBusy === "asr" ? "..." : asrProviderDraft.toUpperCase()}
                  </span>
                </button>
                <button
                  type="button"
                  className="header-runtime-entity"
                  onClick={() => void onChangeProvider("tts")}
                  disabled={providerBusy !== null}
                  aria-label="Toggle TTS provider"
                >
                  <span>TTS</span>
                  <span className={`runtime-provider-word ${ttsProviderDraft}`}>
                    {providerBusy === "tts" ? "..." : ttsProviderDraft.toUpperCase()}
                  </span>
                </button>
                <button
                  type="button"
                  className="header-runtime-refresh"
                  onClick={() => aiRuntime.refetch()}
                  disabled={aiRuntime.isFetching || providerBusy !== null}
                  aria-label="Refresh runtime status"
                  title="Refresh runtime status"
                >
                  {aiRuntime.isFetching ? "…" : "↻"}
                </button>
              </div>
            )}
            <div className="shell-header-actions">
              <Link to="/app/session" className="shell-header-cta">
                Continue session
              </Link>
            </div>
          </div>
          <div className="topbar-alerts">
          {showMissingKey && (
            <article className="panel stack" aria-live="polite">
              <strong>OpenAI key is not configured.</strong>
              <p>App continues in lightweight mode. Add your key in profile to unlock full AI coaching quality.</p>
              <Link to="/app/profile#openai-key-input">Open profile settings</Link>
            </article>
          )}
          {showInvalidKey && (
            <article className="panel stack" aria-live="polite">
              <strong>{keyIssue?.title}</strong>
              <p>{keyIssue?.message}</p>
              <Link to="/app/profile#openai-key-input">Review API key settings</Link>
            </article>
          )}
          {showStatusUnknown && (
            <article className="panel stack" aria-live="polite">
              <strong>Unable to check OpenAI key status.</strong>
              <p>App may run in lightweight mode while connection checks are unavailable.</p>
            </article>
          )}
          {showLocalRuntimeIssue && (
            <article className="panel stack" aria-live="polite">
              <strong>Local runtime needs attention.</strong>
              <p>One or more local modules are not ready. Open profile and review AI Runtime Providers diagnostics.</p>
              <Link to="/app/profile">Open runtime diagnostics</Link>
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
