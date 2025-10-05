#!/bin/sh
set -e

# Simple one-shot database initialization for first run.
# If the SQLite DB file does not exist, create it and seed sample data.

DB_PATH="${DB_PATH:-/data/opentapwall.db}"
DB_DIR="$(dirname "$DB_PATH")"

mkdir -p "$DB_DIR"

if [ ! -f "$DB_PATH" ]; then
  echo "[entrypoint] Initializing sample database at $DB_PATH"
  python - <<'PYCODE'
from sqlmodel import Session, select
from app.db import engine  # creates tables via metadata.create_all + lightweight migrate
from app.models import Beer, DisplaySettings

with Session(engine) as session:
    # Seed beers only if totally empty
    if not session.exec(select(Beer).limit(1)).first():
        session.add_all([
            Beer(tap_number=1, name="Pale Ale", style="APA", abv=5.2, ibu=35, ebc=12),
            Beer(tap_number=2, name="Stout", style="Dry Stout", abv=4.5, ibu=40, ebc=80),
            Beer(tap_number=3, name="IPA", style="West Coast IPA", abv=6.5, ibu=60, ebc=18),
        ])
    if not session.get(DisplaySettings, 1):
        session.add(DisplaySettings())
    session.commit()
PYCODE
else
  echo "[entrypoint] Existing database found at $DB_PATH (skipping seed)"
fi

exec "$@"
