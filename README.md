# OpenTapWall
![OpenTapWall](OpenTapWall.png)

Single-container FastAPI app to display and manage a tap list on a TV or screen. Designed for bars, taprooms, and homebrew setups. Runs on any host including single-board computers (Raspberry Pi, etc.). Single Docker image — SQLite + a mounted volume for persistence. Seeds three sample beers on first start.

## Features

### Public Wall (`/`)
- Three layout modes: **Grid** (smart column count), **Carousel** (animated horizontal scroll), **Vertical** (portrait cards side by side)
- Tap number badge and optional price badge overlaid on beer image
- ABV / IBU / EBC stat badges
- Dark and light themes with user-defined accent color
- Optional logo and background image (with glassmorphism card effect)
- Optional background darkening overlay in dark mode
- Header (title + logo) can be hidden for a cleaner display
- Smart auto-refresh: polls `/beers/` every 20 s, only reloads if data changed (no flicker)
- Text auto-scales to fit card width — no clipping, card dimensions unchanged
- Admin button revealed on mouse move (hidden at rest)

### Admin UI (`/admin`)
- **Display settings**: title, accent color, dark/light theme, layout (grid/carousel/vertical), currency, logo upload, background upload/remove, hide header toggle
- **Beer management**: create, edit (tap #, name, style, ABV, IBU, EBC, price), delete, image upload, show/hide per beer (on tap / hidden)
- Settings auto-saved when navigating back to the wall
- 63 supported currencies

### Technical
- FastAPI + SQLModel + SQLite (WAL mode)
- All images stored as BLOBs in the database — no filesystem writes at runtime
- Additive runtime migration — new columns added safely on startup, no Alembic needed
- No frontend build step — Jinja2 templates + vanilla CSS + vanilla JS

## Quick Start

### Docker Compose (recommended)
```bash
docker build -t opentapwall:latest .
docker compose up -d
```

Open:
- Wall: http://localhost:8000/
- Admin: http://localhost:8000/admin

### Manual Docker run
```bash
docker build -t opentapwall:latest .
mkdir -p opentapwall_data
docker run -d \
  --name opentapwall \
  -p 8000:8000 \
  -v $(pwd)/opentapwall_data:/data \
  opentapwall:latest
```

### Development (hot reload)
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

> **Note:** When CSS/JS/template changes don't appear after a rebuild, use `docker build --no-cache -t opentapwall:latest .` — the legacy builder aggressively caches the `COPY . .` layer.

## Environment Variables

| Variable  | Default                 | Purpose          |
|-----------|-------------------------|------------------|
| `DB_PATH` | `/data/opentapwall.db`  | SQLite file path |

## Data Persistence

All state lives under `/data` (mapped to `./opentapwall_data` by the compose file). This includes the SQLite database, which stores beers, settings, and all image BLOBs. Back up by copying that directory.

To reset to the sample data:
```bash
rm opentapwall_data/opentapwall.db
docker compose restart
```

## API

| Method | Path                       | Purpose                                  |
| --------| ----------------------------| ------------------------------------------|
| GET    | `/`                        | Public tap wall (HTML)                   |
| GET    | `/admin`                   | Admin UI (HTML)                          |
| GET    | `/beers/`                  | List beers (JSON, ordered by tap_number) |
| GET    | `/beers/{id}`              | Single beer (JSON)                       |
| POST   | `/beers/`                  | Create beer (JSON)                       |
| POST   | `/beers/create`            | Create beer (multipart form)             |
| PATCH  | `/beers/{id}`              | Partial update (JSON)                    |
| DELETE | `/beers/{id}`              | Delete beer                              |
| POST   | `/beers/upload-image/{id}` | Attach image to beer (1 MB cap)          |
| PATCH  | `/settings`                | Update display settings (JSON)           |
| POST   | `/settings/logo`           | Upload logo (1 MB cap)                   |
| POST   | `/settings/background`     | Upload background image (5 MB cap)       |
| GET    | `/images/{id}`             | Serve stored image (24 h cache)          |

## CI/CD

`.github/workflows/docker-publish.yml` builds and pushes multi-arch images (`linux/amd64` + `linux/arm64`) to Docker Hub on pushes to `main` and on version tags (`vX.Y.Z`). Requires secrets: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`.

## Support me
If you find this app useful, support me on [Ko-fi](https://ko-fi.com/olivercorrodi)!
