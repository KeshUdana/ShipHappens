# ShipHappens — MVP Running Instructions

AI-powered exam paper generator. Upload past papers → review the extracted blueprint → generate a new paper with live progress → edit/regenerate questions → export with answer key and originality check.

## Architecture

```
Frontend (Next.js, :3000)  →  Backend (FastAPI, :8000)  →  Google Gemini + Supabase (Postgres)
```

The AI layer lives inside the backend (`backend/ai/`) — there is no separate AI service. The only external dependencies are the Gemini API and the Supabase database.

## Prerequisites

- **Python 3.13+** with [uv](https://docs.astral.sh/uv/) installed
- **Node.js 20+** with npm
- `backend/.env` populated (already in the repo checkout) — must contain at minimum:
  - `DATABASE_URL` — Supabase Postgres connection string
  - `GOOGLE_API_KEY` — Gemini API key (Gemini calls are billed/limited on the **Google** side)
- 1–2 real past-paper **PDFs** on hand for the demo — the repo does not ship any.

## Start the app

**Terminal 1 — backend:**

```powershell
cd backend
uv run uvicorn app.main:app --port 8000
```

Expected output ends with `Uvicorn running on http://0.0.0.0:8000`.
Verify: open http://localhost:8000/health → `{"status": "healthy", "app": "ShipHappens"}`.
Interactive API docs: http://localhost:8000/docs

**Terminal 2 — frontend:**

```powershell
cd frontend
npm install        # first time only
npm run dev
```

Open http://localhost:3000 — the dashboard should load. Click **Generate Paper** to enter the wizard.

> The frontend reads `NEXT_PUBLIC_API_URL` from `frontend/.env.local` (defaults to `http://localhost:8000`).

## The demo flow (4-step wizard)

| Step | What you do | What to expect |
|------|-------------|----------------|
| 1. Upload | Drag in 1–5 past-paper PDFs, optionally set title/board/level, click **Analyze & Generate Blueprint** | "Uploading…" then "Extracting blueprint…" for **~30–60 s** (Gemini reads the PDFs), then auto-advance |
| 2. Blueprint | Review the extracted structure (sections, marks, tone, mark distribution), click **Generate New Paper** | Live progress bar driven by real streaming events ("Writing Section A…") for **~1–2 min**. A yellow marks-drift warning toast is normal — that's the validator |
| 3. Edit | Hover any question → **Edit** (instant, local) or **Regenerate** (~10–20 s, replaces the question with a new one worth the same marks). Sections can be regenerated too | Edited/regenerated content is spliced into the paper in place |
| 4. Export | **Print / Save PDF** (browser print-to-PDF) · **Generate Answer Key** (~30–60 s, model answers + marking criteria from your *edited* paper) · **Check Originality** (~10–30 s, flags overlap with the source PDFs) | A print-ready paper, a full marking scheme, and similarity warnings if any |

## Rules & gotchas

- **Do not refresh the page mid-wizard.** The generated paper lives in browser memory — F5 restarts the flow from step 1.
- **Port 8000 already in use** (`[WinError 10048] only one usage of each socket address`): an old backend instance is still running. Free the port:

  ```powershell
  Get-NetTCPConnection -LocalPort 8000 -State Listen |
    Select-Object -ExpandProperty OwningProcess -Unique |
    ForEach-Object { Stop-Process -Id $_ -Force }
  ```

- **Blueprint extraction fails with "No uploaded files found"**: the upload step didn't complete — re-upload the PDFs.
- **Generation errors / quota messages**: the Gemini key has hit its rate limit — wait a minute and retry. Generation uses `gemini-2.5-flash` for streaming.
- **CORS errors in the browser console**: the backend only allows origins `localhost:3000/5173/8080` — make sure the frontend is on port 3000.
- Do a **full silent dry run** with your actual demo PDFs before presenting, so you know the real timings on your connection.

## Useful endpoints (backend, for debugging)

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness check |
| `GET /docs` | Swagger UI for every endpoint |
| `POST /sessions/` | Create a session |
| `POST /sessions/{id}/uploads/` | Upload a PDF (multipart) |
| `POST /sessions/{id}/blueprint/` | Extract blueprint from uploads |
| `POST /sessions/{id}/generate/stream` | Generate paper (SSE stream) |
| `POST /sessions/{id}/regenerate/question` | Regenerate one question |
| `POST /sessions/{id}/answer-key/` | Generate answer key for a paper |
| `POST /sessions/{id}/dedup/` | Check paper originality vs. sources |
