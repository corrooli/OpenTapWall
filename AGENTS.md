# AGENTS.md — OpenTapWall

Guidance for AI agents (Claude Code, Copilot, etc.) working in this repo.

## Project Summary

Single-container FastAPI app serving a tap-list display wall and admin UI. Backend: Python / FastAPI / SQLModel / SQLite. Frontend: Jinja2 templates + vanilla CSS. Deployed as a Docker image (multi-arch: amd64 + arm64).

## Repo Layout

```
app/
  main.py          # FastAPI app, startup seed, image/settings routes
  models.py        # SQLModel schemas: Beer, DisplaySettings, StoredImage
  db.py            # Engine setup, SQLite pragmas, lightweight migration
  crud.py          # Beer CRUD functions (get/create/update/delete)
  routers/
    beers.py       # /beers/* endpoints + image upload
  static/          # CSS files (style_admin.css, style_wall.css)
  templates/       # Jinja2 HTML (index.html = wall, admin.html = admin)
Dockerfile
docker-entrypoint.sh   # DB init + uvicorn start
requirements.txt
.github/workflows/docker-publish.yml   # Build + push multi-arch image to Docker Hub
```

## Architecture

- **No ORM relationships** — `image_id` / `logo_image_id` are plain integer FKs; joins done manually.
- **Images as BLOBs** — all images stored in `StoredImage` table, served via `GET /images/{id}`. No filesystem images at runtime.
- **Singleton settings row** — `DisplaySettings` always has `id=1`; upsert pattern used everywhere.
- **Lightweight migration** — `db._lightweight_migrate()` runs at startup; adds nullable columns idempotently. No Alembic.
- **No auth** — admin UI is open. Security is out-of-scope for now.

## Environment Variables

| Variable   | Default                  | Purpose               |
|------------|--------------------------|-----------------------|
| `DB_PATH`  | `/data/opentapwall.db`   | SQLite file path      |

## API Endpoints

| Method | Path                          | Purpose                       |
|--------|-------------------------------|-------------------------------|
| GET    | `/`                           | Public tap wall               |
| GET    | `/admin`                      | Admin UI                      |
| GET    | `/beers/`                     | List beers (JSON)             |
| GET    | `/beers/{id}`                 | Single beer                   |
| POST   | `/beers/`                     | Create beer (JSON)            |
| POST   | `/beers/create`               | Create beer (form, admin)     |
| PATCH  | `/beers/{id}`                 | Partial update                |
| DELETE | `/beers/{id}`                 | Delete beer                   |
| POST   | `/beers/upload-image/{id}`    | Attach image to beer          |
| PATCH  | `/settings`                   | Update display title          |
| POST   | `/settings/logo`              | Upload logo image             |
| GET    | `/images/{id}`                | Serve stored image            |

## Key Constraints

- **Image size cap**: 1 MB for both beer images and logos (enforced in router and `main.py`).
- **SQLite WAL mode** — pragmas set on connect; safe for single-process use, not horizontal scale.
- **No tests exist yet** — no test suite. When adding tests, use a real SQLite (no mocks); `pytest` + `httpx` + `TestClient` is the expected stack.
- **Python 3.13** — `str | None` union syntax used throughout; do not regress to `Optional` unless needed for SQLModel compat.

## Development

Local dev with hot reload (bind-mount source):
```bash
docker run --rm -it \
  -p 8000:8000 \
  -v $(pwd):/code \
  -v $(pwd)/opentapwall_data:/data \
  opentapwall:latest \
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Or without Docker:
```bash
pip install -r requirements.txt
DB_PATH=opentapwall_data/opentapwall.db uvicorn app.main:app --reload
```

## CI/CD

`.github/workflows/docker-publish.yml` triggers on push to `main` and `v*.*.*` tags. Builds `linux/amd64` + `linux/arm64` and pushes to Docker Hub. Requires secrets: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`.

## Agent Guidelines

- **Run migrations first** — if modifying schema, update `models.py` AND add the additive ALTER in `db._lightweight_migrate()`.
- **No filesystem writes at runtime** — images go to `StoredImage` table, not disk.
- **Keep it small** — this is a hobby single-binary-style app. Avoid framework sprawl, unnecessary abstractions, or new dependencies without good reason.
- **Admin UI is Jinja2 + vanilla JS** — no frontend build step. Keep it that way unless asked.
- **Test the wall and admin in browser** for any UI change — there is no automated UI test.
