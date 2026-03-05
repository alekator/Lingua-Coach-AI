# LinguaCoach Desktop Shell

Minimal Electron wrapper for the `web` app.

## Run with local Vite frontend

1. Start web dev server in another terminal:

```powershell
cd ..\web
npm run dev
```

2. Start Electron shell:

```powershell
cd ..\desktop
npm install
npm run start:web
```

## Run with built frontend

```powershell
cd ..\web
npm run build
cd ..\desktop
npm install
npm run start
```
