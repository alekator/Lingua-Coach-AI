# LinguaCoach AI

Multilingual AI language coach with two runtime modes:
- OpenAI API mode (`openai`)
- Fully local model mode (`local`)

Supports:
- Web app (Vite + React)
- Desktop app (Electron shell over web UI)
- Dockerized backend services (`api`, `asr`, `tts`, `postgres`)

---

## 1. What this project does

LinguaCoach AI is a local-first language learning coach with:
- onboarding + placement test
- isolated learning spaces per language pair
- daily session flow and next-best-action loop
- chat coaching with rubric-based feedback
- speaking practice (ASR + coach feedback + optional TTS reply)
- text + voice translation
- vocabulary + SRS review
- drills, roleplay scenarios, grammar analyzer, homework
- streaks, skill map, CEFR skill-tree, timeline, achievements, weekly checkpoints
- backup/restore and full reset
- AI runtime provider switching (OpenAI/Local) for LLM, ASR, TTS
- diagnostics and health endpoints for runtime status

---

## 2. Architecture

Services:
- `services/api` - main FastAPI orchestrator, DB models, routing, coaching logic
- `services/asr` - speech-to-text provider service (OpenAI/local)
- `services/tts` - text-to-speech provider service (OpenAI/local)
- `postgres` - main DB in Docker mode
- `web` - React SPA
- `desktop` - Electron wrapper that opens the web UI

High-level flow:
1. UI sends requests to API (`:8000`)
2. API calls ASR (`:8001`) and TTS (`:8002`) as needed
3. Runtime provider per module can be `openai` or `local`
4. UI can switch providers from Profile -> AI Runtime Providers

---

## 3. Tech stack

Backend:
- Python 3.12 (in Docker), FastAPI, Pydantic, SQLAlchemy, Alembic, Uvicorn
- OpenAI SDK (`openai`)
- Local LLM: `llama-cpp-python` (GGUF)
- Local ASR: `faster-whisper` or HuggingFace Whisper folder via `transformers+torch`
- Local TTS: `qwen-tts` / `transformers+torch` path depending on model type

Frontend:
- React 18, TypeScript, Vite
- React Query, Zustand, React Router
- Vitest + Testing Library
- Playwright smoke tests

Desktop:
- Electron

Infra:
- Docker Compose (base/dev/prod/local-model overlays)
- GitHub Actions CI (lint/test/build + e2e smoke)

---

## 4. Repository map

- `services/api` - core API, app routes, migrations, API tests
- `services/asr` - ASR microservice + tests
- `services/tts` - TTS microservice + tests
- `web` - frontend app + unit tests + playwright
- `desktop` - electron shell
- `scripts` - smoke scripts and local all-in-one launcher
- `docker-compose.yml` - base stack
- `docker-compose.dev.yml` - live-reload overlay
- `docker-compose.prod.yml` - prod-like overlay
- `docker-compose.local-models.yml` - local-model provider overlay

---

## 5. Prerequisites

Required:
- Docker Desktop running
- Node.js 20+
- npm 10+ (or equivalent npm bundled with Node)
- Python 3.11+ (for local test commands outside Docker)

For Local AI runtime mode:
- pre-downloaded local model files on disk
- enough RAM/CPU for local inference

---

## 6. Supported runtime modes

Set in `.env`:

```env
API_LLM_PROVIDER=openai   # or local
ASR_PROVIDER=openai       # or local
TTS_PROVIDER=openai       # or local
```

You can also switch providers at runtime in UI:
- Profile -> AI Runtime Providers
- choose provider per module (LLM/ASR/TTS)
- Save provider settings
- Refresh status

Diagnostics shown in UI:
- provider status (`ok`, `disabled`, `error`)
- model path
- dependency availability
- device
- load/probe timings

---

## 7. Models for local mode

Expected local paths example:

```text
F:\AI_MODELS_GENERIC\LINGUA_MODELS
  \qwen2.5-7b\qwen2.5-7b-instruct-q4_k_m.gguf
  \whisper-small\...
  \qwen3-tts\...
```

Set either direct paths:

```env
LOCAL_LLM_MODEL_PATH=F:\AI_MODELS_GENERIC\LINGUA_MODELS\qwen2.5-7b\qwen2.5-7b-instruct-q4_k_m.gguf
LOCAL_ASR_MODEL_PATH=F:\AI_MODELS_GENERIC\LINGUA_MODELS\whisper-small
LOCAL_TTS_MODEL_PATH=F:\AI_MODELS_GENERIC\LINGUA_MODELS\qwen3-tts
```

Or set root + rely on compose local overlay defaults:

```env
LOCAL_MODELS_ROOT=F:\AI_MODELS_GENERIC\LINGUA_MODELS
```

Notes:
- Local LLM expects GGUF file for `llama-cpp-python`.
- Local ASR supports:
  - faster-whisper converted model folder (`model.bin`)
  - HF Whisper folder (`pytorch_model.bin`, config, tokenizer)
- Local TTS supports Qwen3-TTS local folder.

Models are not stored in this repository.

---

## 8. Environment variables (full reference)

Base keys from `.env.example`:

```env
OPENAI_API_KEY=sk-...

API_LLM_PROVIDER=openai
ASR_PROVIDER=openai
TTS_PROVIDER=openai

LOCAL_LLM_MODEL_PATH=
LOCAL_ASR_MODEL_PATH=
LOCAL_TTS_MODEL_PATH=
LOCAL_MODELS_ROOT=
LOCAL_LLM_N_CTX=4096
LOCAL_LLM_N_THREADS=6
LOCAL_ASR_DEVICE=auto
LOCAL_ASR_COMPUTE_TYPE=int8

OPENAI_CHAT_MODEL=gpt-4.1-mini
OPENAI_VOICE_MODEL=gpt-4.1-mini
OPENAI_TRANSLATE_MODEL=gpt-4.1-mini
OPENAI_ASR_MODEL=whisper-1
OPENAI_TTS_MODEL=tts-1
OPENAI_CHAT_MAX_OUTPUT_TOKENS=320
OPENAI_VOICE_MAX_OUTPUT_TOKENS=180
OPENAI_TRANSLATE_MAX_OUTPUT_TOKENS=180
OPENAI_TEMPERATURE_CHAT=0.4
OPENAI_TEMPERATURE_VOICE=0.3
OPENAI_TEMPERATURE_TRANSLATE=0.0

AI_CACHE_MAX_ITEMS=512

DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/linguacoach
ASR_URL=http://asr:8001
TTS_URL=http://tts:8002
API_PORT=8000
ASR_PORT=8001
TTS_PORT=8002
POSTGRES_DB=linguacoach
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

Optional/advanced envs used by services:
- `TTS_AUDIO_DIR` (path for generated audio files in TTS service)

Important:
- Placeholder `OPENAI_API_KEY=sk-...` is treated as not configured.
- Keep Windows paths absolute and unquoted.

---

## 9. Install and run (quick)

### 9.1 Create `.env`

```powershell
Copy-Item .env.example .env
```

### 9.2 Start Docker stack (default OpenAI mode)

```powershell
docker compose up -d --build
```

### 9.3 Dev hot-reload mode for backend

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

### 9.4 Local-model mode (Docker + mounted models + local deps)

```powershell
docker compose -f docker-compose.yml -f docker-compose.local-models.yml up -d --build
```

### 9.5 Start web UI

```powershell
cd web
npm install
npm run dev
```

Open `http://localhost:5173`.

### 9.6 Start desktop UI

In a second terminal:

```powershell
cd desktop
npm install
npm run start:web
```

---

## 10. One-command local start (web + desktop + backend)

Script:
- `scripts/start-local-all.ps1`

Run from repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-local-all.ps1
```

If Docker stack already running:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-local-all.ps1 -SkipDocker
```

This script:
- starts local-model docker stack
- starts web dev server
- starts electron desktop shell

---

## 11. Full runbook (from zero to working app)

1. Ensure Docker Desktop is running.
2. Clone repo.
3. Create `.env` from `.env.example`.
4. Fill provider mode and model paths (OpenAI or Local).
5. Build/start stack:
   - OpenAI mode: `docker compose up -d --build`
   - Local mode: `docker compose -f docker-compose.yml -f docker-compose.local-models.yml up -d --build`
6. Verify backend health:
   - `http://localhost:8000/health`
   - `http://localhost:8001/health`
   - `http://localhost:8002/health`
7. Start web:
   - `cd web && npm install && npm run dev`
8. Start desktop (optional):
   - `cd desktop && npm install && npm run start:web`
9. Open app and complete first-launch setup:
   - choose native/target language
   - choose goal
   - run placement test
10. Open Profile -> AI Runtime Providers and verify statuses.

---

## 12. Health and diagnostics endpoints

Core:
- `GET /health` on each service:
  - API `:8000/health`
  - ASR `:8001/health`
  - TTS `:8002/health`

Runtime:
- API:
  - `GET /settings/ai-runtime`
  - `POST /settings/ai-runtime`
- ASR:
  - `GET /asr/provider`
  - `POST /asr/provider`
  - `GET /asr/diagnostics`
- TTS:
  - `GET /tts/provider`
  - `POST /tts/provider`
  - `GET /tts/diagnostics`

Useful checks:

```powershell
Invoke-WebRequest http://localhost:8000/settings/ai-runtime?probe=false -UseBasicParsing
Invoke-WebRequest http://localhost:8001/asr/diagnostics -UseBasicParsing
Invoke-WebRequest http://localhost:8002/tts/diagnostics -UseBasicParsing
```

---

## 13. Feature list (product capabilities)

Onboarding and profile:
- first launch setup
- placement test
- dynamic language pair spaces
- workspace switch + per-space progress isolation

Coach loop:
- daily plan and session progression (start -> progress -> complete)
- next-best-action loop
- reactivation recommendations

Practice modules:
- coach chat
- speaking practice with:
  - file upload
  - microphone recording in UI
  - ASR transcription
  - rubric/feedback
  - optional TTS coach audio reply
- translation:
  - text translate
  - voice translate (file or microphone)
- vocabulary + SRS
- drills
- roleplays / scenario tracks
- grammar analyzer
- homework

Progress and retention:
- streaks
- skill map
- CEFR skill-tree
- achievements/rewards
- weekly goal + weekly review + weekly checkpoint
- timeline and journal
- outcomes and report

Data control:
- export backup JSON
- import backup
- full reset with confirmation

---

## 14. API overview (main routes)

App/profile/settings:
- `GET /app/bootstrap`
- `POST /app/reset`
- `GET /app/backup/export`
- `POST /app/backup/restore`
- `POST /profile/setup`
- `GET /profile`
- `POST /profile/placement-test/start`
- `POST /profile/placement-test/answer`
- `POST /profile/placement-test/finish`
- `GET /settings/openai-key`
- `POST /settings/openai-key`
- `GET /settings/ai-runtime`
- `POST /settings/ai-runtime`
- `GET /settings/usage-budget`
- `POST /settings/usage-budget`
- `GET /settings/language-capabilities`

Workspaces:
- `GET /workspaces`
- `POST /workspaces`
- `PATCH /workspaces/{workspace_id}`
- `POST /workspaces/switch`
- `GET /workspaces/active`
- `GET /workspaces/overview`
- `DELETE /workspaces/{workspace_id}`

Chat/voice/translation:
- `POST /chat/start`
- `POST /chat/message`
- `POST /chat/end`
- `POST /voice/transcribe`
- `POST /voice/message`
- `GET /voice/progress`
- `POST /translate`
- `POST /translate/voice`

Learning and coach:
- `POST /grammar/analyze`
- `POST /exercises/generate`
- `POST /exercises/grade`
- `GET /plan/today`
- `GET /coach/session/today`
- `GET /coach/session/progress`
- `POST /coach/session/progress`
- `GET /coach/error-bank`
- `GET /coach/next-actions`
- `GET /coach/review-queue`
- `GET /coach/daily-challenge`
- `GET /coach/trajectory`
- `GET /coach/roadmap`
- `GET /coach/outcome-packs`
- `GET /coach/reactivation`
- `GET /scenarios`
- `GET /coach/scenario-tracks`
- `GET /scenarios/script`
- `POST /scenarios/select`
- `POST /scenarios/turn`

Vocab/homework/progress:
- `GET /vocab`
- `POST /vocab/add`
- `POST /vocab/review/next`
- `POST /vocab/review/submit`
- `POST /homework/create`
- `GET /homework`
- `POST /homework/submit`
- `GET /progress/summary`
- `GET /progress/skill-map`
- `GET /progress/skill-tree`
- `GET /progress/streak`
- `GET /progress/weekly-review`
- `GET /progress/weekly-checkpoint`
- `GET /progress/outcomes`
- `GET /progress/achievements`
- `GET /progress/report`
- `GET /progress/timeline`
- `GET /progress/journal`
- `GET /progress/weekly-goal`
- `POST /progress/weekly-goal`
- `GET /progress/rewards`
- `POST /progress/rewards/claim`

ASR/TTS service routes:
- ASR: `GET /asr/provider`, `POST /asr/provider`, `GET /asr/diagnostics`, `POST /asr/transcribe`
- TTS: `GET /tts/provider`, `POST /tts/provider`, `GET /tts/diagnostics`, `POST /tts/speak`, `GET /audio/{file_name}`

---

## 15. Testing

Backend tests:

```powershell
cd services/api
python -m pytest -q

cd ..\asr
python -m pytest -q

cd ..\tts
python -m pytest -q
```

Web tests:

```powershell
cd web
npm test
npm run build
```

Web e2e smoke:

```powershell
cd web
npm run test:e2e:smoke
```

PowerShell smoke scripts from repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\e2e-smoke.ps1 -BaseUrl http://localhost:8000 -UserId 1
powershell -ExecutionPolicy Bypass -File .\scripts\e2e-key-paths.ps1 -BaseUrl http://localhost:8000 -UserId 1
powershell -ExecutionPolicy Bypass -File .\scripts\e2e-workspace-journey.ps1 -BaseUrl http://localhost:8000 -UserId 1
powershell -ExecutionPolicy Bypass -File .\scripts\e2e-local-runtime.ps1 -BaseUrl http://localhost:8000 -UserId 1
```

---

## 16. CI

CI pipeline runs:
- backend lint + tests
- web tests + build
- API e2e smoke (critical paths)
- Playwright UI smoke

Workflow location:
- `.github/workflows/ci.yml`

---

## 17. Smoke checklist (manual QA)

After startup validate:

1. Health endpoints all return 200.
2. First launch setup completes and routes to dashboard.
3. AI runtime status loads in Profile (no `Failed to load AI runtime status`).
4. Provider switching in Profile works (OpenAI/Local) for all 3 modules.
5. Chat responds.
6. Speaking:
   - file upload works
   - microphone recording works
   - ASR transcript appears
   - coach response appears
   - audio reply works when TTS available
7. Translate:
   - text translation works
   - voice translation works via upload and recording
8. Word bank + SRS works.
9. Drills/Roleplays/Grammar/Homework return responses.
10. Create second workspace and confirm progress isolation.
11. Backup export/import works.
12. Start-over reset returns app to first launch.
13. Theme toggle works and active nav item remains readable in both themes.

---

## 18. Troubleshooting

### Script path errors (PowerShell)
Run commands from repo root (`README.md` folder), not from `desktop` subfolder.

### `Failed to load AI runtime status`
Rebuild API + ASR + TTS:

```powershell
docker compose -f docker-compose.yml -f docker-compose.local-models.yml up -d --build api asr tts
```

### Local diagnostics show missing dependencies
Rebuild local stack with local overlay:

```powershell
docker compose -f docker-compose.yml -f docker-compose.local-models.yml up -d --build
```

### ASR 500 / transcribe errors
Check ASR logs:

```powershell
docker compose -f docker-compose.yml -f docker-compose.local-models.yml logs asr --tail 200
```

### TTS unavailable / audio playback unavailable
Check TTS diagnostics and logs:

```powershell
Invoke-WebRequest http://localhost:8002/tts/diagnostics -UseBasicParsing
docker compose -f docker-compose.yml -f docker-compose.local-models.yml logs tts --tail 200
```

### OpenAI mode not working
Verify:
- valid key saved (Profile -> OpenAI API key)
- billing/quota available in OpenAI account
- providers set to `OpenAI` in Profile AI Runtime Providers

### Desktop opens but UI blank
Ensure web dev server is running on `http://localhost:5173` before `npm run start:web`.

---

## 19. Stop and cleanup

Stop local-model stack:

```powershell
docker compose -f docker-compose.yml -f docker-compose.local-models.yml down
```

Stop base stack:

```powershell
docker compose down
```

Stop web/desktop terminals:
- `Ctrl + C` in their terminal windows

---

## 20. Notes for contributors

- Keep model files outside git.
- Keep `.env` private.
- Do not commit `node_modules`, generated audio, local caches.
- When changing API contracts, update this README and frontend client contracts.
- Before push: run backend tests + web tests + web build.

