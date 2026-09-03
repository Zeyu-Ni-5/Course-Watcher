# Course Watcher v2

Course Watcher is a FastAPI service that monitors University of Waterloo course enrollment using the official UW Open Data API.

Course Watcher v2 adds a protected English natural-language parsing preview and a public Railway deployment while preserving all v1 Watch endpoints.

`POST /parse` never creates a Watch. Review its four-field response, then send the accepted values to `POST /watches`.

## Features

- Create, list, retrieve, update, and delete course watches
- Optionally monitor a specific component, such as `LEC`, `LAB`, or `TUT`
- Use the current UW term automatically or accept an explicit term code
- Filter watches by active or inactive status
- Check live enrollment through the official UW Open Data API
- Display each matching section as `OPEN` or `FULL`
- Store a new enrollment snapshot after every successful status check
- Preserve snapshot history instead of overwriting previous results
- Reject duplicate watches at both the service and database levels
- Preview one English natural-language course request through `POST /parse`
- Provide interactive API documentation through FastAPI Swagger UI

## Technology Stack

- Python 3.12+
- FastAPI, Uvicorn, SQLAlchemy 2, Pydantic 2, HTTPX
- OpenAI Python SDK (for the protected parse preview)
- SQLite by default
- pytest

## Requirements

- Python 3.12 or newer
- A UW Open Data API key for live status checks
- An internet connection for live status checks

Apply for a UW API key at <https://uwaterloo.ca/api/>. See the [UW Open Data API documentation](https://openapi.data.uwaterloo.ca/api-docs/index.html).

## Installation

Run these commands from the `Course-Watcher v2` directory:

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
```

If `python` is not available on Windows, use `py` instead for the virtual-environment command.

## Environment Variables

### UW API key

Store the key in `UW_API_KEY`; do not put it in source code or upload it to GitHub.

In PowerShell, set `UW_API_KEY` in the current terminal to your private API-key value (without printing it).

### Database URL

The optional `DATABASE_URL` selects the database connection. If unset, the service uses `sqlite:///./course_watcher.db`.

## Parse Environment Variables

- `APP_ACCESS_TOKEN`: private value required in the `X-Token` request header.
- `OPENAI_API_KEY`: OpenAI API credential; never commit it.
- `MODEL_NAME`: optional override; defaults to `gpt-5.6-luna`.

The OpenAI API is billed separately from ChatGPT. Do not put any secret in source code, `.env` examples, screenshots, logs, or Git history.

## Running the API

Development server:

```powershell
uvicorn app.main:app --reload
```

Production/Railway command (Railway supplies `$PORT`):

```powershell
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

The health check is `GET /health` and returns `{"status":"ok"}`. FastAPI documentation is available at `/docs`; the OpenAPI document is at `/openapi.json`.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Public service health check |
| `POST` | `/parse` | Protected one-course natural-language preview |
| `POST` | `/watches` | Create a course watch |
| `GET` | `/watches` | List watches, optionally filtered by `active` |
| `GET` | `/watches/{watch_id}` | Retrieve one watch |
| `PATCH` | `/watches/{watch_id}` | Pause or resume a watch |
| `DELETE` | `/watches/{watch_id}` | Delete a watch and its snapshots |
| `GET` | `/watches/{watch_id}/status` | Check live section status and save snapshots |

## Parse Examples

`Watch CS 136 lectures in Fall 2026` returns `CS`, `136`, `LEC`, and `1269`.

`Watch CS 136` returns null component and term values.

`Watch CS 136 and ECE 106` is rejected because v2 parses exactly one explicit course.

Send the accepted four fields from the preview to `POST /watches`. Include the private `APP_ACCESS_TOKEN` in the `X-Token` header when calling `/parse`.

## Watch API

Create a watch for all components of CS 136 in a specific term:

```json
{
  "subject": "CS",
  "catalog": "136",
  "component": null,
  "term_code": "1269"
}
```

Create a lecture-only watch by setting `"component": "LEC"`. Both `component` and `term_code` are optional: null component means all components, and an omitted term requests the current term from UW. Subjects and components are normalized to uppercase; a term code must contain exactly four digits.

List or filter watches with `GET /watches`, `GET /watches?active=true`, or `GET /watches?active=false`. Pause/resume with `PATCH /watches/{watch_id}` and `{"active": false}` or `true`.

Check availability with `GET /watches/1/status`. A matching section is `OPEN` only when `enrolled_total < capacity`; otherwise it is `FULL`. Each successful check stores one `Snapshot` row per matching section.

## Data Storage

The `watches` table stores course and monitoring configuration. The `snapshots` table stores enrollment state for each successful check. One watch can have many snapshots; deleting a watch also deletes its snapshots.

## Railway Deployment

1. Create a Railway project and add a service from this repository.
2. In the service **Settings**, set the builder to **Railpack**.
3. In the service **Settings**, set the start command to:

   ```text
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

4. In the service **Settings**, set the healthcheck path to `/health` and the healthcheck timeout to **100 seconds**.
5. In the service **Variables** tab, add `UW_API_KEY`, `APP_ACCESS_TOKEN`, and `OPENAI_API_KEY`. Add `MODEL_NAME` or `DATABASE_URL` only when overriding their defaults. Use private values; never paste secrets into this README.
6. In the service **Settings**, open **Networking** and select **Generate Domain**. Verify `https://<generated-domain>/health` returns `{"status":"ok"}`.

New Railway services cannot opt into legacy Config as Code, so this repository intentionally has no `railway.json`. Railway's current Infrastructure as Code flow requires a linked project and a successful `railway config plan`; use it only as a separately authorized deployment step. See Railway's [Config as Code](https://docs.railway.com/config-as-code) and [Infrastructure as Code](https://docs.railway.com/infrastructure-as-code) documentation.

## Railway Deployment Limitation

This deployment uses SQLite on Railway's ephemeral container filesystem without a Volume. Watch and Snapshot data may disappear after a restart or redeployment. The hosted service is a demonstration, not durable production storage.

Persistent storage with a Railway Volume or PostgreSQL is outside the scope of this project.

## Testing

Run the complete suite from this directory:

```powershell
python -m pytest -q
```

Tests use an isolated in-memory SQLite database. UW and OpenAI behavior is mocked, so the suite does not send real requests. Coverage includes request normalization, all watch endpoints, duplicate protection, API errors, component filtering, `OPEN`/`FULL` calculation, snapshots, cascade deletion, parse validation, token security, and parser retry/error handling.

## Error Handling

Errors are structured JSON with a `detail` field. Invalid requests return `422`, missing resources `404`, duplicate watches `409`, model/UW failures `502`, and missing parse configuration `503`.

## Responsible API Use and Project Scope

Use only the official UW API, keep credentials out of source control, avoid high-frequency requests, and use polling intervals of at least 15 minutes. Scheduled checks, notifications, multi-user subscriptions, production database migrations, and a frontend dashboard are intentionally outside the scope of this project.

The service only reports availability; it does not register users for courses.
