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
  - `POST /tts/speak` (on tts service)
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

## Quality / Platform Features

- Request tracing: all responses include `X-Request-ID`.
- Unified API error shape:
  - `{"error":"...", "detail":"...", "request_id":"..."}`
- Basic in-memory rate limit in API.
- JSON-style access logs in API middleware.

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
