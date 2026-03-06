# LinguaCoach-AI

Dockerized MVP backend for an AI language tutor:
- `services/api` (FastAPI orchestrator)
- `services/asr` (speech-to-text service)
- `services/tts` (text-to-speech service)
- `postgres` (database)

## Requirements

- Docker Desktop (or Docker Engine + Compose)
- Python 3.11+ (for local tests)

## AI Runtime Modes (OpenAI + Local Models)

LinguaCoach supports two runtime modes:
- `openai` (default)
- `local` (self-hosted models on your machine)

Switch via `.env`:

```powershell
API_LLM_PROVIDER=openai   # or local
ASR_PROVIDER=openai       # or local
TTS_PROVIDER=openai       # or local
```

Local model paths:

```powershell
LOCAL_LLM_MODEL_PATH=F:\AI_MODELS_GENERIC\LINGUA_MODELS\qwen2.5-7b\qwen2.5-7b-instruct-q4_k_m.gguf
LOCAL_ASR_MODEL_PATH=F:\AI_MODELS_GENERIC\LINGUA_MODELS\whisper-small
LOCAL_TTS_MODEL_PATH=F:\AI_MODELS_GENERIC\LINGUA_MODELS\qwen3-tts
```

ASR local supports two model folder formats:
- `faster-whisper` converted folder (contains `model.bin`)
- Hugging Face Whisper folder (for example `openai/whisper-small`, contains `pytorch_model.bin`)

OpenAI fallback remains available for each component when provider is set to `openai`.

## Quick Start

1. Copy env file:

```powershell
Copy-Item .env.example .env
```

2. Start stack:

```powershell
docker compose up -d --build
```

Dev mode with live reload for Python services:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

Local-model mode (LLM + ASR + TTS from mounted model volume):

```powershell
docker compose -f docker-compose.yml -f docker-compose.local-models.yml up -d --build
```

Note: `docker-compose.local-models.yml` enables extra local-runtime dependencies inside
containers (`llama-cpp-python`, `faster-whisper`, `numpy/transformers/torch`).

Prod-like mode:

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

3. Run database migrations (optional for local SQLite dev, required for Postgres flow):

```powershell
cd services/api
..\..\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
cd ..\..
```

4. Health checks:

```powershell
Invoke-WebRequest http://localhost:8000/health -UseBasicParsing
Invoke-WebRequest http://localhost:8001/health -UseBasicParsing
Invoke-WebRequest http://localhost:8002/health -UseBasicParsing
```

Compose config validation:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml config > $null
docker compose -f docker-compose.yml -f docker-compose.prod.yml config > $null
```

## One-Command Local Start (Web + Desktop + Local Models)

If you already downloaded models (LLM/STT/TTS), you can start everything with one command:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-local-all.ps1
```

This script does:
- starts backend stack in local-model mode (`docker-compose.yml + docker-compose.local-models.yml`)
- starts web dev server (`web/npm run dev`)
- starts desktop shell (`desktop/npm run start:web`)
- builds local-runtime dependencies for `api/asr/tts` automatically

If backend containers are already running and you only need web + desktop:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-local-all.ps1 -SkipDocker
```

Required `.env` fields for local mode:

```powershell
API_LLM_PROVIDER=local
ASR_PROVIDER=local
TTS_PROVIDER=local
LOCAL_MODELS_ROOT=F:\AI_MODELS_GENERIC\LINGUA_MODELS
LOCAL_LLM_MODEL_PATH=F:\AI_MODELS_GENERIC\LINGUA_MODELS\qwen2.5-7b\qwen2.5-7b-instruct-q4_k_m.gguf
LOCAL_ASR_MODEL_PATH=F:\AI_MODELS_GENERIC\LINGUA_MODELS\whisper-small
LOCAL_TTS_MODEL_PATH=F:\AI_MODELS_GENERIC\LINGUA_MODELS\qwen3-tts
```

Stop local-mode backend containers:

```powershell
docker compose -f docker-compose.yml -f docker-compose.local-models.yml down
```

## Full Runbook: From Zero to Running (Web + Desktop, Models Already Downloaded)

This is the full sequential path for a new user on Windows PowerShell.
Assumption: model files are already downloaded on disk.

### 0. Prerequisites

- Docker Desktop is installed and running.
- Node.js 20+ is installed.
- Python 3.11+ is installed.
- Git repo is cloned.
- You run commands from repository root (folder with `README.md`, `docker-compose.yml`, `scripts`).

Quick root check:

```powershell
Get-ChildItem README.md, docker-compose.yml, scripts\start-local-all.ps1
```

### 1. Prepare `.env`

Create local env file:

```powershell
Copy-Item .env.example .env
```

Open `.env` and set local runtime values:

```powershell
API_LLM_PROVIDER=local
ASR_PROVIDER=local
TTS_PROVIDER=local
LOCAL_MODELS_ROOT=F:\AI_MODELS_GENERIC\LINGUA_MODELS
LOCAL_LLM_MODEL_PATH=F:\AI_MODELS_GENERIC\LINGUA_MODELS\qwen2.5-7b\qwen2.5-7b-instruct-q4_k_m.gguf
LOCAL_ASR_MODEL_PATH=F:\AI_MODELS_GENERIC\LINGUA_MODELS\whisper-small
LOCAL_TTS_MODEL_PATH=F:\AI_MODELS_GENERIC\LINGUA_MODELS\qwen3-tts
```

Important:
- keep paths absolute;
- do not wrap paths in quotes;
- use the real path on your machine.

### 2. Start everything with one command

From repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-local-all.ps1
```

What this command starts:
- Docker services (`api`, `asr`, `tts`, `postgres`) in local-model profile;
- web dev server (`http://localhost:5173`);
- desktop shell (Electron window).

If Docker is already running and you only need web+desktop:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-local-all.ps1 -SkipDocker
```

### 3. Verify backend availability

Run:

```powershell
Invoke-WebRequest http://localhost:8000/health -UseBasicParsing
Invoke-WebRequest http://localhost:8001/health -UseBasicParsing
Invoke-WebRequest http://localhost:8002/health -UseBasicParsing
Invoke-WebRequest http://localhost:8000/settings/ai-runtime?probe=false -UseBasicParsing
Invoke-WebRequest http://localhost:8001/asr/diagnostics -UseBasicParsing
Invoke-WebRequest http://localhost:8002/tts/diagnostics -UseBasicParsing
```

Expected:
- all requests return `200`;
- `/settings/ai-runtime` reports providers you set (`local` or `openai`);
- diagnostics include explicit status/message for each module.

### 4. Open app (both modes)

- Web: open `http://localhost:5173`
- Desktop: Electron window should open automatically from the start script.

If desktop did not open:

```powershell
cd desktop
npm install
npm run start:web
cd ..
```

### 5. First Launch Setup

In onboarding screen:
- choose native/target language pair;
- set goal and preferences;
- run placement test;
- if using OpenAI mode, optionally save key;
- if using local mode, key is not required.

After placement test finish, app should route to main dashboard/session flow.

## Smoke Checklist (Full, End-to-End)

Use this checklist after startup to confirm real working state.

### A. Runtime and diagnostics

1. Open `Profile`.
2. Find `AI Runtime Providers`.
3. Set providers (`OpenAI` or `Local`) for `LLM / ASR / TTS`.
4. Click `Save provider settings`.
5. Click `Refresh status`.
6. Confirm diagnostics block shows module-by-module status:
   - provider,
   - model path,
   - dependency availability,
   - device,
   - load/probe timings,
   - readable error if not ready.

Expected:
- no `Failed to load AI runtime status`;
- statuses reflect current env/provider selection.

### B. Onboarding and workspace baseline

1. Start from first-launch flow.
2. Complete placement test.
3. Verify dashboard loads.
4. Open `Profile` -> `Learning Spaces` and confirm active space exists.

Expected:
- active space created;
- CEFR/goal data saved;
- no blocking errors.

### C. Core learning paths

1. `Daily Session`:
   - open next step;
   - mark started/completed.
2. `Coach Chat`:
   - send one user message;
   - receive response/rubric/fallback depending on provider status.
3. `Speaking`:
   - upload short audio file;
   - get transcription/feedback.
4. `Translate`:
   - run text translation;
   - run voice translation via file upload.
5. `Word Bank`:
   - add word;
   - run one review action.
6. `Drills`:
   - generate drill set;
   - submit one answer.
7. `Roleplays`:
   - open available scenario;
   - send one turn.
8. `Grammar`:
   - submit sentence;
   - get corrections.
9. `Homework`:
   - create one homework item;
   - submit a response.

Expected:
- all screens render;
- actions return responses (full mode or fallback mode with clear messaging);
- no crashes/navigation loops.

### D. Multi-space persistence

1. In `Profile`, create second language pair workspace.
2. Switch to it and do at least one activity.
3. Switch back to first workspace.
4. Confirm previous progress is still there.
5. Switch again to second workspace and confirm its isolated progress.

Expected:
- per-space isolation works;
- switching is fast and stable;
- progress persists across switches.

### E. Theme, responsive, and desktop shell

1. Toggle Light/Dark theme button.
2. Confirm active menu item is clearly visible in both themes.
3. Confirm styled file picker appears consistent.
4. Resize desktop window to narrow width and verify sidebar/mobile behavior.

Expected:
- theme changes instantly;
- readability and contrast remain good;
- layout remains usable on narrow widths.

### F. Backup / restore / reset safety

1. In `Profile`, run `Export backup (JSON)`.
2. Verify file downloaded.
3. Import same backup.
4. (Optional) run Start Over flow and confirm double-confirm behavior.

Expected:
- backup/import succeeds without corruption;
- reset requires confirmation and returns to first-launch state.

### G. API-level smoke scripts

Run from repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\e2e-smoke.ps1 -BaseUrl http://localhost:8000 -UserId 1
powershell -ExecutionPolicy Bypass -File .\scripts\e2e-key-paths.ps1 -BaseUrl http://localhost:8000 -UserId 1
powershell -ExecutionPolicy Bypass -File .\scripts\e2e-workspace-journey.ps1 -BaseUrl http://localhost:8000 -UserId 1
```

Optional local runtime latency run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\e2e-local-runtime.ps1 -BaseUrl http://localhost:8000 -UserId 1
```

Expected:
- scripts finish without failing assertions;
- local runtime script prints timings.

## Common Launch Mistakes and Fixes

- Script not found (`start-local-all.ps1`):
  - you are in wrong folder; return to repo root.
- `Failed to load AI runtime status`:
  - rebuild local stack:
  ```powershell
  docker compose -f docker-compose.yml -f docker-compose.local-models.yml up -d --build
  ```
- Local diagnostics show missing deps (`llama-cpp-python`, `faster-whisper`, `numpy`):
  - pull latest repo and rebuild local containers with `--build`.
- Desktop opens but blank:
  - ensure web dev server is running on `5173`, then restart `npm run start:web` in `desktop`.

## Stop / Cleanup

Stop backend:

```powershell
docker compose -f docker-compose.yml -f docker-compose.local-models.yml down
```

Stop web/desktop:
- close terminal windows started by the local script, or press `Ctrl + C` in each running terminal.

## User Quick Guide (future-proof)

Use this section as the shortest setup for new users.

1. Prepare models outside the repo (example root):
   - `F:\AI_MODELS_GENERIC\LINGUA_MODELS\qwen2.5-7b\qwen2.5-7b-instruct-q4_k_m.gguf`
   - `F:\AI_MODELS_GENERIC\LINGUA_MODELS\whisper-small`
   - `F:\AI_MODELS_GENERIC\LINGUA_MODELS\qwen3-tts`
2. Create `.env` from template:

```powershell
Copy-Item .env.example .env
```

3. In `.env`, set local runtime and model paths:

```powershell
API_LLM_PROVIDER=local
ASR_PROVIDER=local
TTS_PROVIDER=local
LOCAL_MODELS_ROOT=F:\AI_MODELS_GENERIC\LINGUA_MODELS
LOCAL_LLM_MODEL_PATH=F:\AI_MODELS_GENERIC\LINGUA_MODELS\qwen2.5-7b\qwen2.5-7b-instruct-q4_k_m.gguf
LOCAL_ASR_MODEL_PATH=F:\AI_MODELS_GENERIC\LINGUA_MODELS\whisper-small
LOCAL_TTS_MODEL_PATH=F:\AI_MODELS_GENERIC\LINGUA_MODELS\qwen3-tts
```

4. Start everything (backend + web + desktop):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-local-all.ps1
```

5. Optional: if docker services are already up, start only web + desktop:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-local-all.ps1 -SkipDocker
```

6. Stop local backend stack:

```powershell
docker compose -f docker-compose.yml -f docker-compose.local-models.yml down
```

## Local Mode Troubleshooting

If Profile shows `Failed to load AI runtime status` or `/settings/ai-runtime` returns `404`:

```powershell
docker compose -f docker-compose.yml -f docker-compose.local-models.yml up -d --build api asr tts
```

If diagnostics show missing local dependencies, rebuild local stack with `--build`:

```powershell
docker compose -f docker-compose.yml -f docker-compose.local-models.yml up -d --build
```

If voice page shows `offline://tts-unavailable` (or message "Audio playback is temporarily unavailable"):
- local TTS generation failed inside `tts` service;
- check exact error:

```powershell
docker compose -f docker-compose.yml -f docker-compose.local-models.yml logs tts --tail 200
```

For Qwen3-TTS specifically, latest `transformers` code may be required.
Pull latest project changes and rebuild local stack:

```powershell
docker compose -f docker-compose.yml -f docker-compose.local-models.yml up -d --build tts api
```

First local build can be long (LLM/TTS dependencies are heavy).
Please wait for build completion before opening Profile diagnostics.

Quick diagnostics checks:

```powershell
Invoke-WebRequest http://localhost:8000/settings/ai-runtime?probe=false -UseBasicParsing
Invoke-WebRequest http://localhost:8001/asr/diagnostics -UseBasicParsing
Invoke-WebRequest http://localhost:8002/tts/diagnostics -UseBasicParsing
```

Expected behavior in local mode:
- `llm_provider/asr_provider/tts_provider` are `local`
- diagnostics `status` is `ok` (or detailed error with exact missing dependency/model path)

If API local LLM build fails with `Could not find compiler ... gcc`, pull latest changes and rebuild.
The project now installs required toolchain automatically for local API image.

## API Highlights

- Profile/onboarding:
  - `GET /app/bootstrap`
  - `POST /app/reset`
  - `GET /app/backup/export`
  - `POST /app/backup/restore`
  - `POST /profile/setup`
  - `POST /profile/placement-test/start`
  - `POST /profile/placement-test/answer`
  - `POST /profile/placement-test/finish`
  - `GET /settings/usage-budget`
  - `POST /settings/usage-budget`
  - `GET /settings/ai-runtime`
  - `POST /settings/ai-runtime`
- Workspaces (multi-language spaces):
  - `GET /workspaces`
  - `POST /workspaces`
  - `PATCH /workspaces/{workspace_id}`
  - `POST /workspaces/switch`
  - `GET /workspaces/active`
  - `GET /workspaces/overview`
  - `DELETE /workspaces/{workspace_id}`
- Chat + memory:
  - `POST /chat/start`
  - `POST /chat/message`
  - `POST /chat/end`
- Translation + TTS:
  - `POST /translate`
  - `POST /translate/voice`
  - `POST /tts/speak` (on tts service)
- Grammar + exercises + planning:
  - `POST /grammar/analyze`
  - `POST /exercises/generate`
  - `POST /exercises/grade`
  - `GET /plan/today`
  - `GET /coach/session/today`
  - `GET /coach/review-queue`
  - `GET /coach/scenario-tracks`
  - `GET /coach/error-bank`
  - `GET /coach/trajectory`
  - `GET /coach/roadmap`
  - `GET /coach/outcome-packs`
  - `GET /scenarios`
  - `POST /scenarios/select`
- Voice pipeline:
  - `POST /voice/transcribe`
  - `POST /voice/message`
  - `GET /voice/progress`
  - `GET /asr/provider` (ASR service)
  - `POST /asr/provider` (ASR service)
  - `GET /asr/diagnostics` (ASR service)
  - `GET /tts/provider` (TTS service)
  - `POST /tts/provider` (TTS service)
  - `GET /tts/diagnostics` (TTS service)
- Vocabulary + SRS:
  - `GET /vocab`
  - `POST /vocab/add`
  - `POST /vocab/review/next`
  - `POST /vocab/review/submit`
- Homework + analytics:
  - `POST /homework/create`
  - `POST /homework/submit`
  - `GET /homework`
  - `GET /progress/summary`
  - `GET /progress/skill-map`
  - `GET /progress/skill-tree`
  - `GET /progress/streak`
  - `GET /progress/journal`
  - `GET /progress/timeline`
  - `GET /progress/weekly-goal`
  - `GET /progress/weekly-review`
  - `GET /progress/weekly-checkpoint`
  - `GET /progress/outcomes`
  - `GET /progress/rewards`
  - `GET /progress/achievements`
  - `GET /progress/report`
  - `GET /coach/daily-challenge`
  - `GET /coach/reactivation`

## API Contract Notes

- `GET /app/bootstrap`
  - returns active workspace context for UI routing and state sync:
    - `active_workspace_id`
    - `active_workspace_native_lang`
    - `active_workspace_target_lang`
    - `active_workspace_goal`

- `POST /app/reset`
  - full local reset for single-user desktop mode.
  - requires payload confirmation token: `"RESET"`.
  - clears users, workspaces, profiles, progress data, and in-process OpenAI key.

- `GET /app/backup/export`
  - returns a full JSON snapshot of local desktop data for backup:
    - workspaces, profiles, sessions/messages, vocab/srs, homework, progress snapshots, usage events.

- `POST /app/backup/restore`
  - requires confirmation token `"RESTORE"`.
  - replaces current local data with the provided JSON snapshot and restores table rows with IDs.

- `GET /workspaces`
  - returns owner scope workspace list:
    - `owner_user_id`
    - `active_workspace_id`
    - `items[]` (`id`, `native_lang`, `target_lang`, `goal`, `is_active`, timestamps)

- `POST /workspaces/switch`
  - activates selected workspace and returns:
    - `active_workspace_id`
    - `active_user_id`

- `GET /workspaces/overview`
  - per-space progress snapshot for dashboard cards:
    - `workspace_id`
    - `native_lang`, `target_lang`, `goal`, `is_active`
    - `has_profile`, `streak_days`, `minutes_practiced`, `words_learned`, `last_activity_at`

- `DELETE /workspaces/{workspace_id}`
  - prevents deleting the last remaining space.
  - response:
    - `deleted_workspace_id`
    - `active_workspace_id` (fallback active space after deletion)

- `GET /plan/today`
  - response includes `adaptation_notes: string[]` with short reasoning for plan adaptation.

- `GET /coach/next-actions`
  - each action may include `quick_mode_minutes` to enable one-click short mode before routing.

- `GET /coach/session/today`
  - returns guided step sequence for the day:
    - `steps[].id`
    - `steps[].title`
    - `steps[].description`
    - `steps[].route`
    - `steps[].duration_minutes`

- `GET /coach/error-bank`
  - returns recurring correction patterns to drive targeted drills:
    - `items[].category`
    - `items[].occurrences`
    - `items[].latest_bad`, `items[].latest_good`
    - `items[].drill_prompt`
    - `items[].suggested_route`

- `GET /coach/review-queue`
  - unified spaced review planner combining:
    - due vocabulary cards
    - recurring error-bank patterns
    - grammar-focused repetitions
    - pronunciation retries

- `GET /coach/reactivation`
  - supports `available_minutes` to build personalized easy-return plans for the real time budget.
  - response includes:
    - `available_minutes`
    - `recommended_minutes`
    - `plan_mode` (`micro|standard|extended`)

- `GET /scenarios`
  - supports optional `user_id` for mastery-gated visibility:
    - `items[].required_level`
    - `items[].unlocked`
    - `items[].gate_reason`
  - locked scenarios are rejected by `POST /scenarios/select` until gate is satisfied.

- `GET /coach/scenario-tracks`
  - goal-based scenario sequences with explicit progress and milestones:
    - `track_id`, `goal`, `title`
    - `completed_steps`, `total_steps`, `completion_percent`
    - `next_scenario_id`
    - `milestones[]` for track progression

- `POST /chat/message`
  - response includes coaching rubric in `rubric`:
    - `overall_score` (0..100)
    - `level_band`
    - `grammar_accuracy`, `lexical_range`, `fluency_coherence`, `task_completion` (each with `score` 1..5 + `feedback`)
    - `strengths[]`
    - `priority_fixes[]`
    - `next_drill`
  - if usage cap is reached, endpoint returns lightweight local fallback guidance instead of failing.

- `POST /translate` and `POST /voice/message`
  - provider/TTS failures degrade to lightweight mode (`200 OK`) with text-first fallback instead of hard `502`.

- `GET /settings/usage-budget`
  - returns per-user usage limits and current consumption:
    - `daily_token_cap`, `weekly_token_cap`, `warning_threshold`
    - `daily_used_tokens`, `weekly_used_tokens`
    - `daily_remaining_tokens`, `weekly_remaining_tokens`
    - `daily_warning`, `weekly_warning`, `blocked`

- `POST /settings/usage-budget`
  - updates per-user budget caps and warning threshold.
  - stored in learner profile preferences for desktop-local persistence.

- `GET /settings/ai-runtime`
  - returns currently active providers and diagnostics for all modules:
    - `llm_provider`, `asr_provider`, `tts_provider`
    - `llm`, `asr`, `tts` diagnostic blocks with:
      - `status`, `message`
      - `model_path`, `model_exists`
      - `dependency_available`, `device`
      - `load_ms`, `probe_ms`

- `POST /settings/ai-runtime`
  - switches runtime providers (`openai|local`) for:
    - LLM in API
    - ASR service
    - TTS service
  - persists selection for next app start in secure/local store.

- `GET /progress/journal`
  - response includes weekly view and actionable recommendations:
    - `weekly_minutes`
    - `weekly_sessions`
    - `weak_areas[]`
    - `next_actions[]`
    - `entries[]` (recent sessions with mode, message count, completion)

- `GET /progress/timeline`
  - chronological history feed with filters:
    - `workspace_id`
    - `skill`
    - `activity_type` (`chat|scenario|correction|vocab_review|homework`)

- `GET /progress/outcomes`
  - learning-outcome snapshot (not only activity):
    - `current_level`
    - `estimated_level_from_skills`
    - `avg_skill_score`
    - `improvement_7d_points`
    - `confidence`
    - `recommendations[]`

- `GET /progress/weekly-checkpoint`
  - explicit before/after checkpoint over a 7-day (configurable) window:
    - `baseline_avg_skill`, `current_avg_skill`
    - `delta_points`, `delta_percent`, `measurable_growth`
    - `top_gain_skill`, `top_gain_points`
    - per-skill deltas in `skills[]`

- `GET /progress/skill-tree`
  - CEFR ladder with transparent completion criteria and progress:
    - `items[].level`, `items[].status`, `items[].progress_percent`
    - `items[].closed_criteria[]`
    - `items[].remaining_criteria[]`

## Quality / Platform Features

- Request tracing: all responses include `X-Request-ID`.
- Unified API error shape:
  - `{"error":"...", "detail":"...", "request_id":"..."}`
- Basic in-memory rate limit in API.
- JSON-style access logs in API middleware.
- AI cost controls:
  - configurable OpenAI models (`OPENAI_CHAT_MODEL`, `OPENAI_VOICE_MODEL`, `OPENAI_TRANSLATE_MODEL`, `OPENAI_ASR_MODEL`)
  - configurable output token caps (`OPENAI_*_MAX_OUTPUT_TOKENS`)
  - configurable temperatures (`OPENAI_TEMPERATURE_*`)
  - lightweight in-memory AI cache (`AI_CACHE_MAX_ITEMS`)

## CI / Automated Checks

GitHub Actions workflow: `.github/workflows/ci.yml`

Runs on every `push` / `pull_request` (and manual `workflow_dispatch`):
- Backend lint (critical Python rules via Ruff) + unit tests (`api`, `asr`, `tts`)
- Web tests + production build
- E2E smoke for critical user paths (`scripts/e2e-key-paths.ps1` + `scripts/e2e-workspace-journey.ps1`) against a started local API in CI
- Browser UI smoke via Playwright (onboarding -> dashboard critical path)
- CI reliability guards: concurrency cancel, job timeouts, dependency caching, API log artifact upload

## Running Tests

```powershell
cd services/api
..\..\.venv\Scripts\python.exe -m pytest tests -q
cd ..\asr
..\..\.venv\Scripts\python.exe -m pytest tests -q
cd ..\tts
..\..\.venv\Scripts\python.exe -m pytest tests -q
cd ..\..
```

Frontend (`web`) tests/build:

```powershell
cd web
npm install
npm run test
npm run build
cd ..
```

## Mobile Web + PWA

Web client is now mobile-ready and can be installed as a Progressive Web App:
- responsive layout tuned for phone/tablet widths
- web manifest (`web/public/manifest.webmanifest`)
- service worker (`web/public/sw.js`) with offline fallback page (`web/public/offline.html`)

Local check:

```powershell
cd web
npm install
npm run build
npm run preview
```

Then open from phone browser on the same network (or deployed host) and install via browser "Add to Home Screen".

Desktop shell (`desktop`):

```powershell
cd desktop
npm install
npm run start:web
cd ..
```

## Local Model Download Guide

Install HuggingFace Hub:

```powershell
pip install huggingface_hub
```

Create local model directory (example):

```powershell
mkdir F:\AI_MODELS_GENERIC\LINGUA_MODELS
```

Download Whisper Small (ASR):

```powershell
python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='openai/whisper-small', local_dir='F:/AI_MODELS_GENERIC/LINGUA_MODELS/whisper-small')"
```

Download Qwen3-TTS (TTS):

```powershell
python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice', local_dir='F:/AI_MODELS_GENERIC/LINGUA_MODELS/qwen3-tts')"
```

Download Qwen2.5 7B GGUF (LLM):

```powershell
python -c "from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='Smoffyy/Qwen2.5-7B-Instruct-Q4_K-M-GGUF', filename='qwen2.5-7b-instruct-q4_k_m.gguf', local_dir='F:/AI_MODELS_GENERIC/LINGUA_MODELS/qwen2.5-7b')"
```

Optional faster download:

```powershell
python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='openai/whisper-small', local_dir='F:/AI_MODELS_GENERIC/LINGUA_MODELS/whisper-small', max_workers=8)"
```

### Optional Python dependencies for local mode

Local providers use optional dependencies and are loaded lazily:

```powershell
pip install llama-cpp-python faster-whisper transformers numpy
```

If dependencies are missing, services return a clear setup error instead of crashing.

## E2E Smoke (Manual)

1. Start stack: `docker compose up -d --build`
2. Create profile:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/profile/setup -ContentType "application/json" -Body '{"user_id":1,"native_lang":"ru","target_lang":"en","level":"A2","goal":"travel","preferences":{}}'
```

3. Start chat:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/chat/start -ContentType "application/json" -Body '{"user_id":1,"mode":"chat"}'
```

4. Add vocab:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/vocab/add -ContentType "application/json" -Body '{"user_id":1,"word":"achieve","translation":"to achieve"}'
```

5. Get progress summary:

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/progress/summary?user_id=1"
```

## E2E Smoke (Script)

End-to-end smoke flow script:
- health check
- bootstrap/onboarding placement flow
- chat lesson
- vocab add
- progress summary validation

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\e2e-smoke.ps1 -BaseUrl http://localhost:8000 -UserId 1
```

Dry run (no network calls):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\e2e-smoke.ps1 -DryRun
```

## E2E Key Paths (Script)

Covers key product flows end-to-end:
- bootstrap + onboarding/placement
- daily planning (`/plan/today`, `/coach/session/today`, next actions, daily challenge, reactivation)
- chat learning turn
- scenario selection + scripted turn
- progress and retention analytics (`summary/journal/weekly-goal/weekly-review/rewards`)

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\e2e-key-paths.ps1 -BaseUrl http://localhost:8000 -UserId 1
```

Dry run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\e2e-key-paths.ps1 -DryRun
```

## E2E Local Runtime (Latency + Stability)

Runs a local-mode smoke and prints request latency summary:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\e2e-local-runtime.ps1 -BaseUrl http://localhost:8000 -UserId 1
```

Optional voice step with real sample:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\e2e-local-runtime.ps1 -BaseUrl http://localhost:8000 -UserId 1 -AudioSamplePath C:\path\sample.wav
```

## E2E Workspace Journey (Script)

Validates multi-space core behavior:
- create second language-pair workspace
- switch between spaces
- isolated progress per workspace user
- bootstrap context follows active workspace
- previous workspace progress persists after return

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\e2e-workspace-journey.ps1 -BaseUrl http://localhost:8000 -UserId 1
```

Dry run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\e2e-workspace-journey.ps1 -DryRun
```

## UI Smoke (Playwright)

Runs browser smoke path for onboarding -> dashboard:

```powershell
cd web
npx playwright install chromium
npm run test:e2e:smoke
cd ..
```

## Eval Harness (P0 Quality Checks)

Runs focused quality guardrails for teacher behavior and scenario content quality:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\eval-harness.ps1
```

