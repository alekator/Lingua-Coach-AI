# LinguaCoach-AI

Dockerized MVP backend for an AI language tutor:
- `services/api` (FastAPI orchestrator)
- `services/asr` (speech-to-text service)
- `services/tts` (text-to-speech service)
- `postgres` (database)

## Requirements

- Docker Desktop (or Docker Engine + Compose)
- Python 3.11+ (for local tests)

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

## API Highlights

- Profile/onboarding:
  - `GET /app/bootstrap`
  - `POST /profile/setup`
  - `POST /profile/placement-test/start`
  - `POST /profile/placement-test/answer`
  - `POST /profile/placement-test/finish`
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
  - `GET /scenarios`
  - `POST /scenarios/select`
- Voice pipeline:
  - `POST /voice/transcribe`
  - `POST /voice/message`
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
  - `GET /progress/streak`
  - `GET /progress/journal`

## API Contract Notes

- `GET /plan/today`
  - response includes `adaptation_notes: string[]` with short reasoning for plan adaptation.

- `GET /coach/session/today`
  - returns guided step sequence for the day:
    - `steps[].id`
    - `steps[].title`
    - `steps[].description`
    - `steps[].route`
    - `steps[].duration_minutes`

- `POST /chat/message`
  - response includes coaching rubric in `rubric`:
    - `overall_score` (0..100)
    - `level_band`
    - `grammar_accuracy`, `lexical_range`, `fluency_coherence`, `task_completion` (each with `score` 1..5 + `feedback`)
    - `strengths[]`
    - `priority_fixes[]`
    - `next_drill`

- `GET /progress/journal`
  - response includes weekly view and actionable recommendations:
    - `weekly_minutes`
    - `weekly_sessions`
    - `weak_areas[]`
    - `next_actions[]`
    - `entries[]` (recent sessions with mode, message count, completion)

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

Desktop shell (`desktop`):

```powershell
cd desktop
npm install
npm run start:web
cd ..
```

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
