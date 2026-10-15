# Course Watcher v3

Waterloo course watch dashboard built with **React + TypeScript + Vite**, connected to the real **FastAPI** backend reused from v2.

## Public deployments

| Service | Address |
| --- | --- |
| Frontend | https://course-watcher-v3-web-production.up.railway.app |
| FastAPI | https://course-watcher-v3-api-production.up.railway.app |
| API health | https://course-watcher-v3-api-production.up.railway.app/health |
| API documentation | https://course-watcher-v3-api-production.up.railway.app/docs |

These are separate Railway services in the existing Course Watcher project. The original v2 service is preserved. Deployment verification is recorded in `docs/verification.md`; generated domain names alone do not prove a working deployment.

## What v3 adds

- Create and view watches, filter by All / Active / Paused, and pause, resume or delete them.
- Check actual section availability on demand, including enrollment, capacity, OPEN/FULL and check time.
- Loading skeletons, empty states, confirmed success messages, readable errors and retry controls.
- Confirmation before deleting a watch and its snapshots.
- Responsive laptop and mobile layouts, labeled controls, keyboard focus and accessible feedback.
- Typed API client, request timeouts, safe 204 handling and cancellation of obsolete enrollment requests.
- Explicit CORS allowlist and separate frontend/backend deployment containers.

The backend models, UW client, service logic, watch routes and protected parse endpoint are reused from v2. The v2 folder remains unchanged.

**Scope:** checks run only when requested. This version does not include a background scheduler, notifications, registration or individual user accounts. Pause updates the watch's active flag and disables the frontend check action. The public demo is shared: everyone can view and modify its watches. Do not enter personal information.

## Folder layout

```text
app/                    Reused FastAPI backend; v3 CORS configuration
tests/                  Backend regression and CORS tests
frontend/src/           React TypeScript dashboard and interaction tests
frontend/Dockerfile     Build with Node; serve static production files with Caddy
Dockerfile              FastAPI production container
scripts/verify_api.py   Real HTTP CRUD and optional enrollment verification
```

## Local development on Windows

Open PowerShell in this v3 folder. Python 3.12+ and Node.js 22.12+ are required.

### Backend terminal

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` privately and set `UW_API_KEY` for live UW checks and automatic current-term lookup. Explicit-term watch CRUD works without a UW key. Then start the backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --env-file .env --host 127.0.0.1 --port 8000
```

### Frontend terminal

```powershell
Set-Location frontend
npm.cmd ci
npm.cmd run dev
```

Open http://127.0.0.1:5173. Development requests to `/api` are forwarded to http://127.0.0.1:8000 by Vite. Leave `VITE_API_BASE_URL` unset locally to use that proxy. Swagger is at http://127.0.0.1:8000/docs.

To test against the hosted backend instead, create `frontend/.env.local` containing its public `VITE_API_BASE_URL`, then restart Vite. Never put a UW or OpenAI key into any `VITE_` variable.

## Environment variables

| Variable | Service | Meaning |
| --- | --- | --- |
| `VITE_API_BASE_URL` | Frontend build | Public HTTPS FastAPI URL; rebuild after changes |
| `CORS_ORIGINS` | Backend | Comma-separated allowed frontend origins, without URL paths |
| `UW_API_KEY` | Backend only | Official Waterloo API key |
| `DATABASE_URL` | Backend | Defaults to `sqlite:///./course_watcher.db` |
| `PORT` | Both hosts | Container listening port, default 8080 |
| `APP_ACCESS_TOKEN`, `OPENAI_API_KEY`, `MODEL_NAME` | Backend only | Optional retained v2 `/parse` configuration |

The current v3 backend is configured for a Railway volume mounted at `/data`, using `sqlite:////data/course_watcher.db`. This is separate from v2 data; v2 rows are not migrated. A volume preserves files across container restarts, but is not a backup. Without a volume, SQLite on a hosting container is ephemeral.

## Tests and production build

From the v3 root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

From `frontend`:

```powershell
npm.cmd test
npm.cmd run build
```

Backend and frontend automated tests isolate external UW/OpenAI or HTTP responses. They do not by themselves prove live enrollment data. The real HTTP smoke check is separate:

```powershell
.\.venv\Scripts\python.exe scripts/verify_api.py --base-url http://127.0.0.1:8000
```

It creates a uniquely named temporary watch, checks list/get/pause/resume/delete and cleans up only its own watch. For a real course check, use `--enrollment --subject CS --catalog 136 --component LEC --term 1269`; choose an actually offered course and term. If the same watch already exists, the script stops without modifying it.

## Deploy separately on Railway

Both Dockerfiles can be deployed with the [Railway CLI](https://docs.railway.com/cli). The [official FastAPI deployment guide](https://docs.railway.com/guides/fastapi) describes Docker and CLI deployment.

1. Create or select a project, then create **two new empty services** for v3. Do not deploy into the original v2 service.
2. Link this v3 root to the API service. Attach a volume at `/data`; set `DATABASE_URL=sqlite:////data/course_watcher.db` and the backend-only UW key. A Railway variable reference can reuse an existing same-project key without copying its value.
3. Deploy the v3 root to the API service with its root Dockerfile. Generate a public domain targeting port 8080. Verify `/health`.
4. Link `frontend/` to the web service. Set `VITE_API_BASE_URL` to the API public URL **before building**, then deploy this frontend directory. Generate another domain targeting port 8080.
5. Set API `CORS_ORIGINS` to the exact web origin, optionally retaining localhost origins for development. Redeploy the API after changing it.
6. Verify public reads and the full watch lifecycle from the published webpage, and test a real course's section status separately.

The web container intentionally fails its build if the production API base URL is missing. It serves the built static app; Vite's development proxy is not used in production. Source-upload and Docker ignore files exclude environments, credentials, local databases, caches and installed dependencies.
