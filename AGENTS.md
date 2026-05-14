# AGENTS.md — OpenTapWall

Guidance for AI agents (Claude Code, Copilot, etc.) working in this repo.

## Project Summary

Single-container FastAPI app serving a tap-list display wall and admin UI. Backend: Python / FastAPI / SQLModel / SQLite. Frontend: Jinja2 templates + vanilla CSS (no build step). Deployed as a Docker image (multi-arch: amd64 + arm64).

## Repo Layout

```
app/
  main.py            # FastAPI app, startup seed, image/settings routes
  models.py          # SQLModel schemas: Beer, DisplaySettings, StoredImage
  db.py              # Engine setup, SQLite pragmas, lightweight migration
  crud.py            # Beer CRUD functions (get/create/update/delete)
  routers/
    beers.py         # /beers/* endpoints + image upload
  static/
    style_wall.css   # Public wall styles
    style_admin.css  # Admin panel styles
  templates/
    index.html       # Public tap wall (grid / carousel / vertical modes)
    admin.html       # Admin panel (settings + beer management)
    beer_card.html   # Shared card partial (used by all three wall modes)
Dockerfile
docker-entrypoint.sh       # DB init + uvicorn start
requirements.txt
.github/workflows/docker-publish.yml  # Build + push multi-arch image to Docker Hub
```

## Architecture

- **No ORM relationships** — `image_id` / `logo_image_id` / `background_image_id` are plain integer FKs; joins done manually.
- **Images as BLOBs** — all images stored in `StoredImage` table, served via `GET /images/{id}`. No filesystem images at runtime.
- **Singleton settings row** — `DisplaySettings` always has `id=1`; upsert pattern used everywhere.
- **Lightweight migration** — `db._lightweight_migrate()` runs at startup; adds nullable columns idempotently via `ALTER TABLE ADD COLUMN`. No Alembic. Always add new columns here when extending the schema.
- **No auth** — admin UI is open. Security is out-of-scope for now.

## Data Models

### Beer
| Field        | Type            | Notes                              |
|--------------|-----------------|------------------------------------|
| id           | int PK          | auto                               |
| tap_number   | int             | display order                      |
| name         | str             | required                           |
| active       | bool            | default True; False = hidden       |
| style        | str \| None     |                                    |
| abv          | float \| None   | Alcohol By Volume %                |
| ibu          | int \| None     | Bitterness                         |
| ebc          | int \| None     | Colour                             |
| og           | float \| None   | Original gravity (unused in UI)    |
| sg           | float \| None   | Specific gravity (unused in UI)    |
| price        | float \| None   | None = price badge hidden          |
| image_id     | int \| None     | FK → StoredImage                   |

### DisplaySettings (singleton id=1)
| Field               | Type         | Default      | Notes                                      |
|---------------------|--------------|--------------|--------------------------------------------|
| title               | str          | "What's on Tap" |                                         |
| accent_color        | str          | "#ffb400"    | Hex; injected as CSS `--accent`            |
| theme               | str          | "dark"       | "dark" or "light"; sets `data-theme`       |
| layout              | str          | "grid"       | "grid", "carousel", or "vertical"          |
| carousel_enabled    | bool         | False        | Legacy; superseded by `layout`             |
| currency            | str          | "EUR"        | Symbol mapped in template                  |
| hide_header         | bool         | False        | Hides title/logo bar on wall               |
| logo_image_id       | int \| None  | None         | FK → StoredImage                           |
| background_image_id | int \| None  | None         | FK → StoredImage; enables glassmorphism    |

### StoredImage
Stores raw image bytes (BLOB). `kind` ∈ `{"beer", "logo", "background"}`.

## Environment Variables

| Variable   | Default                  | Purpose          |
|------------|--------------------------|------------------|
| `DB_PATH`  | `/data/opentapwall.db`   | SQLite file path |

## API Endpoints

| Method | Path                       | Purpose                                      |
| --------| ----------------------------| ----------------------------------------------|
| GET    | `/`                        | Public tap wall (HTML)                       |
| GET    | `/admin`                   | Admin UI (HTML)                              |
| GET    | `/beers/`                  | List all beers (JSON, ordered by tap_number) |
| GET    | `/beers/{id}`              | Single beer (JSON)                           |
| POST   | `/beers/`                  | Create beer (JSON body)                      |
| POST   | `/beers/create`            | Create beer (multipart form, used by admin)  |
| PATCH  | `/beers/{id}`              | Partial update (JSON, BeerUpdate schema)     |
| DELETE | `/beers/{id}`              | Delete beer                                  |
| POST   | `/beers/upload-image/{id}` | Attach image BLOB to beer (1 MB cap)         |
| PATCH  | `/settings`                | Update display settings (JSON, many fields)  |
| POST   | `/settings/logo`           | Upload logo BLOB (1 MB cap)                  |
| POST   | `/settings/background`     | Upload background BLOB (5 MB cap)            |
| GET    | `/images/{id}`             | Serve stored image with 24 h cache header    |

## CSS / Theming Architecture

**Critical:** `--accent` is **never** defined in the CSS files. It is injected exclusively via an inline `<style>` tag in each template:

```html
<style>:root { --accent: {{ settings.accent_color }}; }</style>
```

If you add `--accent` to a CSS file, the external stylesheet will override the inline value (same specificity, later wins) and the user's accent color choice will be ignored.

Theme switching uses `data-theme="dark|light"` on `<html>`. All color tokens are defined in `[data-theme="dark"]` and `[data-theme="light"]` selectors in each stylesheet.

### Wall layout modes (index.html)
Three mutually exclusive layouts based on `settings.layout`:

- **grid** — responsive CSS grid; `data-cols` attribute (1–4) set by `bestCols(n)` JS function; column count computed from beer count.
- **carousel** — horizontal strip. `initCarousel()` JS temporarily adds `is-scrolling` to measure overflow, then removes it if cards fit (fill mode). If cards overflow, clones items for seamless loop at 25 px/s.
- **vertical** — `display: flex; flex-direction: row` with `flex: 1 1 0` cards; portrait cards side by side, all visible, no animation.

### Beer card layout
`.beer-card` uses `display: grid; grid-template-rows: 1fr auto`:
- Row 1 (`1fr`): `.image-wrap` — image fills all available height, shrinks freely.
- Row 2 (`auto`): `.beer-info` — always fully visible, never clipped regardless of card height.

This guarantees beer name / style / stat badges are never hidden even on short cards.

### Text fitting
`fitAllText()` in index.html runs on `load` and `resize`. Steps `.beer-name` and `.beer-style` font-size down from the CSS `clamp()` value until `scrollWidth ≤ clientWidth`. Card dimensions are never changed.

### Background image + dark mode dimming
When `background_image_id` is set, a `linear-gradient(rgba(0,0,0,0.42), rgba(0,0,0,0.42))` overlay is prepended to the `background-image` inline style in dark mode, darkening the wallpaper without affecting card content.

## Key Constraints

- **Image size caps**: 1 MB for beer images and logos; 5 MB for background images (enforced in router / `main.py`).
- **SQLite WAL mode** — pragmas set on connect; safe for single-process use, not horizontal scale.
- **No tests exist yet** — when adding tests, use real SQLite (no mocks); `pytest` + `httpx` + `TestClient` is the expected stack.
- **Python 3.13** — `str | None` union syntax used throughout; do not regress to `Optional` unless required for SQLModel compat.
- **SQLAlchemy 2.x DDL** — `conn.exec_driver_sql(...)` for raw SQL in migrations; must call `conn.commit()` explicitly after DDL or writes.
- **Starlette 0.36+** — use keyword-arg form: `TemplateResponse(request=request, name=..., context=...)`.

## Schema Migration Pattern

When adding a new column:

1. Add field to `models.py` (the SQLModel class).
2. Add `(col_name, "SQL_TYPE DEFAULT val")` tuple to the appropriate loop in `db._lightweight_migrate()`.
3. If it's a settings field, also add `Optional[...]` to `DisplaySettingsUpdate`.
4. Update admin template + JS save payload.

Example from `db.py`:
```python
for col, definition in [
    ("layout", "VARCHAR DEFAULT 'grid'"),
    ("hide_header", "INTEGER DEFAULT 0"),
]:
    if col not in ds_cols:
        conn.exec_driver_sql(f"ALTER TABLE displaysettings ADD COLUMN {col} {definition}")
conn.commit()  # required — SQLAlchemy 2.x does not auto-commit DDL
```

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

- **Schema changes require two edits**: `models.py` (field) + `db.py` (ALTER TABLE). Miss either and the app breaks or silently ignores the new column.
- **No `--accent` in CSS files** — see Theming section above. This has caused bugs before.
- **No filesystem writes at runtime** — images go to `StoredImage` table, not disk.
- **No frontend build step** — Jinja2 + vanilla JS + vanilla CSS only. Do not introduce npm, bundlers, or framework dependencies.
- **Keep it small** — simple app. Avoid framework sprawl, unnecessary abstractions, or new dependencies, only recommend if it helps with simplicity.
- **Test the wall and admin in browser** for any UI change — no automated UI tests exist.
- **Rebuild with `--no-cache`** when CSS/JS/template changes don't appear — legacy Docker builder caches the `COPY . .` layer.
