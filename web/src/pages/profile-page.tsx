import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { EmptyState, ErrorState, LoadingState } from "../components/feedback";
import { FilePicker } from "../components/file-picker";
import { LanguagePairSelector } from "../components/language-pair-selector";
import { getErrorMessage } from "../lib/errors";
import { languageLabelByCode, normalizeLanguageCode } from "../lib/languages";
import { clearWorkspaceRoutes } from "../lib/workspace-routes";
import { syncWorkspaceContext, toBootstrapStorePayload } from "../lib/workspace-context";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";

export function ProfilePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const userId = useAppStore((s) => s.userId) ?? 1;
  const activeWorkspaceId = useAppStore((s) => s.activeWorkspaceId);
  const setBootstrapState = useAppStore((s) => s.setBootstrapState);
  const [nativeLang, setNativeLang] = useState("");
  const [targetLang, setTargetLang] = useState("");
  const [level, setLevel] = useState("");
  const [goal, setGoal] = useState("");
  const [newNativeLang, setNewNativeLang] = useState("");
  const [newTargetLang, setNewTargetLang] = useState("");
  const [newGoal, setNewGoal] = useState("");
  const [workspaceError, setWorkspaceError] = useState("");
  const [placementError, setPlacementError] = useState("");
  const [workspaceBusy, setWorkspaceBusy] = useState(false);
  const [retakeOpen, setRetakeOpen] = useState(false);
  const [retakeSessionId, setRetakeSessionId] = useState<number | null>(null);
  const [retakeQuestion, setRetakeQuestion] = useState("");
  const [retakeQuestionIndex, setRetakeQuestionIndex] = useState(0);
  const [retakeTotalQuestions, setRetakeTotalQuestions] = useState(0);
  const [retakeAnswer, setRetakeAnswer] = useState("");
  const [retakeBusy, setRetakeBusy] = useState(false);
  const [resetConfirmOpen, setResetConfirmOpen] = useState(false);
  const [resetToken, setResetToken] = useState("");
  const [resetBusy, setResetBusy] = useState(false);
  const [resetError, setResetError] = useState("");
  const [backupBusy, setBackupBusy] = useState(false);
  const [backupError, setBackupError] = useState("");
  const [restoreConfirmOpen, setRestoreConfirmOpen] = useState(false);
  const [restoreToken, setRestoreToken] = useState("");
  const [restoreBusy, setRestoreBusy] = useState(false);
  const [restoreError, setRestoreError] = useState("");
  const [restoreFileName, setRestoreFileName] = useState("");
  const [restoreSnapshot, setRestoreSnapshot] = useState<Record<string, unknown> | null>(null);
  const [timelineWorkspaceId, setTimelineWorkspaceId] = useState<number | "all">("all");
  const [timelineSkill, setTimelineSkill] = useState("all");
  const [timelineActivityType, setTimelineActivityType] = useState("all");
  const pushToast = useToastStore((s) => s.push);
  const profile = useQuery({
    queryKey: ["profile", userId],
    queryFn: () => api.profileGet(userId),
  });
  const skillMap = useQuery({
    queryKey: ["skill-map", userId],
    queryFn: () => api.progressSkillMap(userId),
  });
  const streak = useQuery({
    queryKey: ["streak", userId],
    queryFn: () => api.progressStreak(userId),
  });
  const skillTree = useQuery({
    queryKey: ["skill-tree", userId],
    queryFn: () => api.progressSkillTree(userId),
  });
  const journal = useQuery({
    queryKey: ["progress-journal", userId],
    queryFn: () => api.progressJournal(userId),
  });
  const workspaces = useQuery({
    queryKey: ["workspaces"],
    queryFn: api.workspacesList,
  });
  const timeline = useQuery({
    queryKey: ["progress-timeline", userId, timelineWorkspaceId, timelineSkill, timelineActivityType],
    queryFn: () =>
      api.progressTimeline({
        user_id: userId,
        workspace_id: typeof timelineWorkspaceId === "number" ? timelineWorkspaceId : undefined,
        skill: timelineSkill === "all" ? undefined : timelineSkill,
        activity_type: timelineActivityType === "all" ? undefined : timelineActivityType,
        limit: 40,
      }),
  });
  useEffect(() => {
    if (!profile.data) return;
    setNativeLang(profile.data.native_lang);
    setTargetLang(profile.data.target_lang);
    setLevel(profile.data.level);
    setGoal(profile.data.goal ?? "");
  }, [profile.data]);

  async function syncBootstrapContext() {
    const bootstrap = await syncWorkspaceContext(queryClient, setBootstrapState);
    if (bootstrap.needs_onboarding) {
      navigate("/", { replace: true });
    }
  }

  async function onCreateWorkspace(event: FormEvent) {
    event.preventDefault();
    setWorkspaceBusy(true);
    try {
      const normalizedNative = normalizeLanguageCode(newNativeLang);
      const normalizedTarget = normalizeLanguageCode(newTargetLang);
      if (!normalizedNative || !normalizedTarget) {
        throw new Error("Please choose both native and target languages.");
      }
      if (normalizedNative === normalizedTarget) {
        throw new Error("Native and target language must be different.");
      }
      await api.workspaceCreate({
        native_lang: normalizedNative,
        target_lang: normalizedTarget,
        goal: newGoal || null,
        make_active: true,
      });
      setWorkspaceError("");
      setNewNativeLang("");
      setNewTargetLang("");
      setNewGoal("");
      await queryClient.invalidateQueries({ queryKey: ["workspaces"] });
      await syncBootstrapContext();
      pushToast("success", "New learning space created");
    } catch (err) {
      const msg = getErrorMessage(err);
      setWorkspaceError(msg);
      pushToast("error", msg);
    } finally {
      setWorkspaceBusy(false);
    }
  }

  async function onSwitchWorkspace(workspaceId: number) {
    if (!workspaceId) return;
    setWorkspaceBusy(true);
    try {
      await api.workspaceSwitch({ workspace_id: workspaceId });
      await syncBootstrapContext();
      setWorkspaceError("");
      pushToast("success", "Learning space switched");
    } catch (err) {
      const msg = getErrorMessage(err);
      setWorkspaceError(msg);
      pushToast("error", msg);
    } finally {
      setWorkspaceBusy(false);
    }
  }

  async function onRetakeStart() {
    setRetakeBusy(true);
    try {
      const started = await api.placementStart({
        user_id: userId,
        native_lang: nativeLang,
        target_lang: targetLang,
      });
      setRetakeOpen(true);
      setRetakeSessionId(started.session_id);
      setRetakeQuestion(started.question);
      setRetakeQuestionIndex(started.question_index);
      setRetakeTotalQuestions(started.total_questions);
      setRetakeAnswer("");
      setPlacementError("");
      pushToast("info", "Placement retake started");
    } catch (err) {
      const msg = getErrorMessage(err);
      setPlacementError(msg);
      pushToast("error", msg);
    } finally {
      setRetakeBusy(false);
    }
  }

  async function onRetakeAnswer(event: FormEvent) {
    event.preventDefault();
    if (!retakeSessionId) return;
    setRetakeBusy(true);
    try {
      const accepted = await api.placementAnswer({
        session_id: retakeSessionId,
        answer: retakeAnswer,
      });
      setRetakeAnswer("");
      if (accepted.done) {
        const finished = await api.placementFinish({ session_id: retakeSessionId });
        await api.profileSetup({
          user_id: userId,
          native_lang: nativeLang,
          target_lang: targetLang,
          level: finished.level,
          goal,
          preferences: profile.data?.preferences ?? {},
        });
        setLevel(finished.level);
        setRetakeOpen(false);
        setRetakeSessionId(null);
        setRetakeQuestion("");
        setRetakeQuestionIndex(0);
        setRetakeTotalQuestions(0);
        setPlacementError("");
        pushToast("success", `Placement updated: ${finished.level}`);
        await skillMap.refetch();
        return;
      }
      setRetakeQuestion(accepted.next_question ?? "");
      setRetakeQuestionIndex(accepted.next_question_index ?? retakeQuestionIndex + 1);
      setPlacementError("");
    } catch (err) {
      const msg = getErrorMessage(err);
      setPlacementError(msg);
      pushToast("error", msg);
    } finally {
      setRetakeBusy(false);
    }
  }

  async function onResetAllData() {
    const token = resetToken.trim().toUpperCase();
    if (token !== "RESET") {
      setResetError("Type RESET to confirm full data deletion.");
      return;
    }
    setResetBusy(true);
    try {
      await api.appReset({ confirmation: token });
      clearWorkspaceRoutes();
      queryClient.clear();
      const bootstrap = await api.bootstrap();
      queryClient.setQueryData(["bootstrap"], bootstrap);
      setBootstrapState(toBootstrapStorePayload(bootstrap));
      setResetError("");
      setResetConfirmOpen(false);
      setResetToken("");
      pushToast("success", "All learning data removed. Starting fresh.");
      navigate("/", { replace: true });
    } catch (err) {
      const msg = getErrorMessage(err);
      setResetError(msg);
      pushToast("error", msg);
    } finally {
      setResetBusy(false);
    }
  }

  async function onExportBackup() {
    setBackupBusy(true);
    try {
      const payload = await api.appBackupExport();
      const json = JSON.stringify(payload, null, 2);
      const nameStamp = new Date().toISOString().replace(/[:]/g, "-").replace("T", "_").slice(0, 19);
      const fileName = `linguacoach-backup-${nameStamp}.json`;
      const blob = new Blob([json], { type: "application/json" });
      if (typeof URL.createObjectURL !== "function") {
        throw new Error("File export is not supported in this environment.");
      }
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setBackupError("");
      pushToast("success", "Backup exported");
    } catch (err) {
      const msg = getErrorMessage(err);
      setBackupError(msg);
      pushToast("error", msg);
    } finally {
      setBackupBusy(false);
    }
  }

  async function onImportBackupFile(file: File | null) {
    if (!file) {
      return;
    }
    try {
      let raw = "";
      if (typeof file.arrayBuffer === "function") {
        const rawBuffer = await file.arrayBuffer();
        raw = new TextDecoder().decode(rawBuffer);
      } else if (typeof (file as File & { text?: () => Promise<string> }).text === "function") {
        raw = await (file as File & { text: () => Promise<string> }).text();
      } else {
        throw new Error("Cannot read selected file in this browser.");
      }
      const parsed = JSON.parse(raw) as { snapshot?: unknown };
      const snapshotCandidate =
        parsed && typeof parsed === "object" && parsed.snapshot && typeof parsed.snapshot === "object"
          ? (parsed.snapshot as Record<string, unknown>)
          : null;
      if (!snapshotCandidate) {
        throw new Error("Invalid backup file: expected { snapshot: {...} } payload.");
      }
      setRestoreSnapshot(snapshotCandidate);
      setRestoreFileName(file.name);
      setRestoreToken("");
      setRestoreError("");
      setRestoreConfirmOpen(true);
      pushToast("info", "Backup loaded. Confirm restore to replace current local data.");
    } catch (err) {
      const msg = getErrorMessage(err);
      setRestoreSnapshot(null);
      setRestoreFileName("");
      setRestoreConfirmOpen(false);
      setRestoreError(msg);
      pushToast("error", msg);
    } finally {
      // no-op
    }
  }

  async function onRestoreBackup() {
    const token = restoreToken.trim().toUpperCase();
    if (token !== "RESTORE") {
      setRestoreError("Type RESTORE to confirm backup restore.");
      return;
    }
    if (!restoreSnapshot) {
      setRestoreError("Load a valid backup file before restoring.");
      return;
    }

    setRestoreBusy(true);
    try {
      await api.appBackupRestore({ confirmation: token, snapshot: restoreSnapshot });
      clearWorkspaceRoutes();
      queryClient.clear();
      const bootstrap = await api.bootstrap();
      queryClient.setQueryData(["bootstrap"], bootstrap);
      setBootstrapState(toBootstrapStorePayload(bootstrap));
      setRestoreError("");
      setRestoreConfirmOpen(false);
      setRestoreToken("");
      setRestoreFileName("");
      setRestoreSnapshot(null);
      pushToast("success", "Backup restored");
      navigate("/", { replace: true });
    } catch (err) {
      const msg = getErrorMessage(err);
      setRestoreError(msg);
      pushToast("error", msg);
    } finally {
      setRestoreBusy(false);
    }
  }

  const skillEntries = skillMap.data
    ? ([
        ["Speaking", skillMap.data.speaking],
        ["Listening", skillMap.data.listening],
        ["Grammar", skillMap.data.grammar],
        ["Vocab", skillMap.data.vocab],
        ["Reading", skillMap.data.reading],
        ["Writing", skillMap.data.writing],
      ] as const)
    : [];

  function scoreToCefrLabel(score: number): "A1" | "A2" | "B1" | "B2" | "C1" | "C2" {
    if (score < 20) return "A1";
    if (score < 35) return "A2";
    if (score < 50) return "B1";
    if (score < 65) return "B2";
    if (score < 80) return "C1";
    return "C2";
  }

  return (
    <section className="panel stack profile-page">
      <header className="profile-hero panel">
        <div>
          <h2>Coach Profile</h2>
          <p>Manage your learning spaces, preferences, and progress signals in one place.</p>
        </div>
        {streak.isSuccess && streak.data.streak_days > 0 && (
          <aside className="streak-float-card" aria-live="polite">
            <strong>{streak.data.streak_days}-day streak</strong>
            <span>
              {streak.data.active_dates.length > 0
                ? `Last active: ${streak.data.active_dates[streak.data.active_dates.length - 1]}`
                : "Keep it alive today"}
            </span>
          </aside>
        )}
      </header>
      <article className="panel stack profile-heavy-card">
        <h3>Learning Spaces</h3>
        <p>Each language pair is an isolated coach space with its own progress and recommendations.</p>
        {workspaces.isPending && <LoadingState text="Loading learning spaces..." />}
        {workspaces.isError && <ErrorState text="Failed to load learning spaces." />}
        {workspaces.isSuccess && (
          <div className="learning-hub-grid">
            <article className="panel stack profile-space-manage">
              <h4>Manage spaces</h4>
              <p>Pick an active learning space from the list.</p>
              <div className="space-list" role="listbox" aria-label="Learning spaces">
              {workspaces.data.items.map((item) => (
                <button
                  key={`space-item-${item.id}`}
                  type="button"
                  className={`space-list-item ${(activeWorkspaceId ?? workspaces.data.active_workspace_id) === item.id ? "active" : ""}`}
                  role="option"
                  aria-selected={(activeWorkspaceId ?? workspaces.data.active_workspace_id) === item.id}
                  onClick={() => onSwitchWorkspace(item.id)}
                  disabled={workspaceBusy}
                >
                  <span className="space-list-item-title">
                    {languageLabelByCode(item.native_lang)} {"->"} {languageLabelByCode(item.target_lang)}
                  </span>
                  <span className="space-list-item-meta">{item.is_active ? "active" : "switch"}</span>
                </button>
              ))}
              </div>
              {workspaceBusy && <p className="space-list-note">Switching active space...</p>}
            </article>
            <form className="panel stack profile-space-create" onSubmit={onCreateWorkspace}>
              <h4>Create new space</h4>
              <p>Launch a new language pair as an isolated learning universe.</p>
              <LanguagePairSelector
                nativeLang={newNativeLang}
                targetLang={newTargetLang}
                onNativeLangChange={setNewNativeLang}
                onTargetLangChange={setNewTargetLang}
                ariaPrefix="New space"
              />
              <label>
                Goal
                <input aria-label="New space goal" value={newGoal} onChange={(e) => setNewGoal(e.target.value)} />
              </label>
              <button
                type="submit"
                className="cta-primary"
                disabled={workspaceBusy || !newNativeLang.trim() || !newTargetLang.trim()}
              >
                {workspaceBusy ? "Creating..." : "Create and switch space"}
              </button>
            </form>
          </div>
        )}
        {workspaceError && <ErrorState text={workspaceError} />}
      </article>
      {profile.isPending && <LoadingState text="Loading profile settings..." />}
      {profile.isError && <ErrorState text="Failed to load profile settings." />}
      {placementError && <ErrorState text={placementError} />}
      {retakeOpen && (
        <form className="panel stack" onSubmit={onRetakeAnswer}>
          <h3>Level Recalibration</h3>
          <p>
            Question {retakeQuestionIndex + 1} / {retakeTotalQuestions}
          </p>
          <p>{retakeQuestion}</p>
          <label>
            Your answer
            <input value={retakeAnswer} onChange={(e) => setRetakeAnswer(e.target.value)} />
          </label>
          <button type="submit" disabled={retakeBusy || !retakeAnswer.trim()}>
            {retakeBusy ? "Checking..." : "Submit answer"}
          </button>
        </form>
      )}
      {(streak.isPending || skillMap.isPending || journal.isPending) && (
        <LoadingState text="Loading profile analytics..." />
      )}
      {(streak.isError || skillMap.isError || journal.isError) && (
        <ErrorState text="Failed to load progress analytics." />
      )}
      {streak.isSuccess && skillMap.isSuccess && streak.data.streak_days === 0 && (
        <EmptyState text="No tracked activity yet. Start a lesson to populate progress." />
      )}
      {(skillMap.isSuccess || skillTree.isSuccess) && (
        <section className="profile-intel-grid">
          {skillMap.isSuccess && (
            <article className="panel stack intel-skill-card">
              <h3>Skill Map</h3>
              {skillEntries.map(([name, value]) => (
                <div key={name} className="skill-row">
                  <p>
                    <strong>{name}</strong>
                    <span className="skill-row-meta">
                      <span>{scoreToCefrLabel(value)}</span>
                      <span>{value.toFixed(1)}</span>
                    </span>
                  </p>
                  <div className="profile-meter" role="img" aria-label={`${name} level`}>
                    <span style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
                  </div>
                </div>
              ))}
            </article>
          )}
          {skillTree.isSuccess && (
            <article className="panel stack intel-tree-card">
              <div className="cefr-head">
                <h3>CEFR Skill Tree</h3>
                <div className="cefr-head-stats">
                  <span className="badge">Current: {skillTree.data.current_level}</span>
                  <span className="badge">Estimated: {skillTree.data.estimated_level_from_skills}</span>
                  <span className="badge">Avg: {skillTree.data.avg_skill_score}</span>
                  <span className="badge">Next: {skillTree.data.next_target_level ?? "C2 (max)"}</span>
                </div>
              </div>
              <div className="cefr-tree">
                {skillTree.data.items.map((item) => (
                  <div key={item.level} className={`cefr-node ${item.status}`}>
                    <div className="cefr-node-head">
                      <strong>{item.level}</strong>
                      <span>{item.status.replace("_", " ")}</span>
                    </div>
                    <div className="profile-meter" role="img" aria-label={`${item.level} progress`}>
                      <span style={{ width: `${Math.max(0, Math.min(100, item.progress_percent))}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </article>
          )}
        </section>
      )}
      {skillTree.isPending && <LoadingState text="Loading CEFR skill tree..." />}
      {skillTree.isError && <ErrorState text="Failed to load CEFR skill tree." />}
      <section className="profile-journey-grid">
        <article className="panel stack profile-heavy-card journal-card">
          <h3>Weekly Journal</h3>
          {journal.isPending && <LoadingState text="Loading weekly journal..." />}
          {journal.isError && <ErrorState text="Failed to load weekly journal." />}
          {journal.isSuccess && (
            <>
              <div className="journal-kpis">
                <span className="badge">Sessions: {journal.data.weekly_sessions}</span>
                <span className="badge">Minutes: {journal.data.weekly_minutes}</span>
                <span className="badge">Weak: {journal.data.weak_areas.join(", ") || "none"}</span>
              </div>
              <div className="journal-columns">
                <div className="stack">
                  <p>
                    <strong>Next actions</strong>
                  </p>
                  {(journal.data.next_actions.length > 0 ? journal.data.next_actions : ["No actions yet"]).slice(0, 3).map((action) => (
                    <p key={action} className="journal-line">
                      {action}
                    </p>
                  ))}
                </div>
                <div className="stack">
                  <p>
                    <strong>Recent sessions</strong>
                  </p>
                  <div className="journal-session-list">
                    {journal.data.entries.length === 0 && <p className="journal-line">No session history yet.</p>}
                    {journal.data.entries.slice(0, 6).map((entry) => (
                      <p key={entry.session_id} className="journal-line">
                        #{entry.session_id} | {entry.mode} | {entry.completed ? "completed" : "in progress"}
                      </p>
                    ))}
                  </div>
                </div>
              </div>
            </>
          )}
        </article>
        <article className="panel stack profile-heavy-card timeline-card">
          <h3>Learning Timeline</h3>
          <div className="timeline-filters">
            <label>
              Workspace
              <select
                aria-label="Timeline workspace filter"
                value={timelineWorkspaceId}
                onChange={(e) =>
                  setTimelineWorkspaceId(e.target.value === "all" ? "all" : Number(e.target.value))
                }
              >
                <option value="all">All spaces</option>
                {(workspaces.data?.items ?? []).map((item) => (
                  <option key={`tl-ws-${item.id}`} value={item.id}>
                    {languageLabelByCode(item.native_lang)} {"->"} {languageLabelByCode(item.target_lang)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Skill
              <select
                aria-label="Timeline skill filter"
                value={timelineSkill}
                onChange={(e) => setTimelineSkill(e.target.value)}
              >
                <option value="all">All skills</option>
                <option value="grammar">Grammar</option>
                <option value="vocab">Vocab</option>
                <option value="pronunciation">Pronunciation</option>
                <option value="speaking">Speaking</option>
                <option value="writing">Writing</option>
              </select>
            </label>
            <label>
              Activity
              <select
                aria-label="Timeline activity filter"
                value={timelineActivityType}
                onChange={(e) => setTimelineActivityType(e.target.value)}
              >
                <option value="all">All activities</option>
                <option value="chat">Chat</option>
                <option value="scenario">Scenario</option>
                <option value="correction">Correction</option>
                <option value="vocab_review">Vocab review</option>
                <option value="homework">Homework</option>
              </select>
            </label>
          </div>
          {timeline.isPending && <LoadingState text="Loading timeline..." />}
          {timeline.isError && <ErrorState text="Failed to load learning timeline." />}
          {timeline.isSuccess && timeline.data.items.length === 0 && (
            <EmptyState text="No timeline items for selected filters yet." />
          )}
          {timeline.isSuccess && (
            <div className="timeline-list">
              {timeline.data.items.map((item) => (
                <article key={item.id} className="timeline-item">
                  <p className="timeline-item-title">{item.title}</p>
                  <p className="timeline-item-detail">{item.detail}</p>
                  <p className="timeline-item-meta">
                    {item.activity_type} | {item.skill_tags.join(", ")} | {item.workspace_label ?? "current space"} | {item.happened_at}
                  </p>
                </article>
              ))}
            </div>
          )}
        </article>
      </section>
      <article className="panel profile-heavy-card profile-actions-hub">
        <section className="profile-action-col">
          <div className="profile-action-head">
            <div>
              <h3>Recalibrate</h3>
              <p>Retake placement and refresh your CEFR baseline.</p>
            </div>
            <div className="profile-action-tags">
              <button
                type="button"
                className="profile-tag-btn"
                disabled={retakeBusy || !nativeLang.trim() || !targetLang.trim()}
                onClick={onRetakeStart}
              >
                {retakeBusy && !retakeOpen ? "Starting..." : "Recalibrate"}
              </button>
            </div>
          </div>
        </section>
        <section className="profile-action-col">
          <div className="profile-action-head">
            <div>
              <h3>Backup & Restore</h3>
              <p>Export data to JSON or restore from backup file.</p>
            </div>
            <div className="profile-action-tags">
              <button type="button" className="profile-tag-btn" onClick={onExportBackup} disabled={backupBusy}>
                {backupBusy ? "Exporting..." : "Export"}
              </button>
              <FilePicker
                id="import-backup-file"
                ariaLabel="Import backup file"
                accept="application/json,.json"
                onFileChange={(file) => void onImportBackupFile(file)}
                disabled={restoreBusy}
              />
            </div>
          </div>
          {restoreConfirmOpen && (
            <div className="panel stack profile-action-confirm">
              <p>Loaded: {restoreFileName || "unknown"}</p>
              <label>
                Type RESTORE to confirm
                <input value={restoreToken} onChange={(e) => setRestoreToken(e.target.value)} />
              </label>
              <div className="row">
                <button
                  type="button"
                  onClick={() => {
                    setRestoreConfirmOpen(false);
                    setRestoreToken("");
                    setRestoreError("");
                  }}
                  disabled={restoreBusy}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={onRestoreBackup}
                  disabled={restoreBusy || restoreToken.trim().toUpperCase() !== "RESTORE"}
                >
                  {restoreBusy ? "Restoring..." : "Restore"}
                </button>
              </div>
            </div>
          )}
          {backupError && <ErrorState text={backupError} />}
          {restoreError && <ErrorState text={restoreError} />}
        </section>
        <section className="profile-action-col profile-action-danger">
          <div className="profile-action-head">
            <div>
              <h3>Start Over</h3>
              <p>Delete all spaces, progress, sessions, and profile data.</p>
            </div>
            {!resetConfirmOpen && (
              <div className="profile-action-tags">
                <button type="button" className="profile-tag-btn danger" onClick={() => setResetConfirmOpen(true)} disabled={resetBusy}>
                  Start over
                </button>
              </div>
            )}
          </div>
          {resetConfirmOpen && (
            <div className="panel stack profile-action-confirm">
              <p>Type RESET to confirm permanent deletion.</p>
              <label>
                Confirmation
                <input value={resetToken} onChange={(e) => setResetToken(e.target.value)} />
              </label>
              <div className="row">
                <button
                  type="button"
                  onClick={() => {
                    setResetConfirmOpen(false);
                    setResetToken("");
                    setResetError("");
                  }}
                  disabled={resetBusy}
                >
                  Cancel
                </button>
                <button type="button" onClick={onResetAllData} disabled={resetBusy || resetToken.trim().toUpperCase() !== "RESET"}>
                  {resetBusy ? "Deleting..." : "Delete all data"}
                </button>
              </div>
            </div>
          )}
          {resetError && <ErrorState text={resetError} />}
        </section>
      </article>
    </section>
  );
}
