# OpenTapWall

Single-container FastAPI app to display and administer a tap list (beers) with images. Designed to run on single-board computers or any small host. Single Docker image using SQLite + a mounted volume for persistence.
Currently only supports beer, other drinks are planned.

## Features
- FastAPI + SQLModel (SQLite file DB)
- Auto-creates DB and seeds sample beers if empty
- Admin UI at `/admin` for:
	- Creating beers
	- Inline edit tap number / name / style
	- Upload images (stored under `/data` volume → exposed via `/static/images`)
	- Delete beers
- Public display wall at `/` optimized for fullscreen TV (dark theme, responsive)
- Lightweight runtime migration adds new nullable columns (e.g. `image`) if missing

## Quick Start (Single Docker Container)
Build the image:
```
docker build -t opentapwall:latest .
```

Run the container with persistence:
```
mkdir -p opentap_data
docker run -d \
	--name opentapwall \
	-p 8000:8000 \
	-v $(pwd)/opentap_data:/data \
	opentapwall:latest
```

Open:
- Wall: http://localhost:8000/
- Admin: http://localhost:8000/admin

### Development (Hot Reload)
Bind mount the source and override the command:
```
docker run --rm -it \
	-p 8000:8000 \
	-v $(pwd):/code \
	-v $(pwd)/opentap_data:/data \
	-e DB_PATH=/data/opentap.db \
	opentapwall:latest \
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Environment Variables
| Variable | Purpose | Default |
|----------|---------|---------|
| `DB_PATH` | SQLite database file path | `/data/opentap.db` |

### Data Persistence
All persistent state (SQLite file + uploaded images) lives under `/data` (mapped to your host `opentap_data` directory). Back it up by copying that folder.

### Adding Python Packages
Add to `requirements.txt` then rebuild the image:
```
docker build -t opentapwall:latest .
```

## API Summary
- `GET /beers/` list beers
- `POST /beers/` create via JSON
- `POST /beers/create` form-create (used by Admin UI)
- `PATCH /beers/{id}` partial update
- `DELETE /beers/{id}` delete
- `POST /beers/upload-image/{id}` attach image file (multipart)

## Lightweight Migration
On startup a simple check ensures new nullable columns (currently `image`) are added if missing.
