"""Database engine setup and lightweight runtime migrations."""

import os
import logging
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError

_db_path = os.getenv("DB_PATH", "/data/opentapwall.db")
DB_URL = _db_path if _db_path.startswith("sqlite:") else f"sqlite:///{_db_path}"

if not _db_path.startswith("sqlite:"):
    os.makedirs(os.path.dirname(_db_path), exist_ok=True)

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_con, _):
    """Apply SQLite pragmas for reliability and modest concurrency."""
    cur = dbapi_con.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA synchronous=NORMAL;")
    cur.execute("PRAGMA foreign_keys=ON;")
    cur.close()


# Ensure models are imported so metadata is populated before table creation
try:
    from . import models
    _ = models  # mark as used so static analyzers don't flag as unused
except ImportError as exc:
    logging.warning("[db] Could not import models pre-create_all: %s", exc)

SQLModel.metadata.create_all(engine)


def _lightweight_migrate():
    """Perform simple additive, idempotent schema adjustments.

    Ensures:
        * beer table has ``image_id`` column
        * displaysettings table with ``logo_image_id`` column and singleton row
        * storedimage table for BLOB image storage
    """
    try:
        with engine.connect() as conn:
            # Determine existing tables
            tables = {r[0] for r in conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if "beer" not in tables:
                logging.info("[migrate] 'beer' table missing; running create_all again")
                SQLModel.metadata.create_all(engine)
                tables = {r[0] for r in conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

            if "beer" in tables:
                result = conn.exec_driver_sql("PRAGMA table_info(beer);")
                existing_cols = {row[1] for row in result.fetchall()}
                for col, definition in [
                    ("image_id", "INTEGER"),
                    ("price", "REAL"),
                    ("active", "INTEGER DEFAULT 1"),
                ]:
                    if col not in existing_cols:
                        try:
                            logging.info("[migrate] Adding '%s' column to beer", col)
                            conn.exec_driver_sql(f"ALTER TABLE beer ADD COLUMN {col} {definition}")
                        except SQLAlchemyError as e:
                            logging.warning("[migrate] Could not add %s column to beer: %s", col, e)

            conn.exec_driver_sql("CREATE TABLE IF NOT EXISTS displaysettings (id INTEGER PRIMARY KEY, title VARCHAR, logo_image_id INTEGER)")
            ds_cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(displaysettings);").fetchall()}
            for col, definition in [
                ("logo_image_id", "INTEGER"),
                ("accent_color", "VARCHAR DEFAULT ‘#ffb400’"),
                ("theme", "VARCHAR DEFAULT ‘dark’"),
                ("carousel_enabled", "INTEGER DEFAULT 0"),
                ("background_image_id", "INTEGER"),
                ("currency", "VARCHAR DEFAULT 'EUR'"),
                ("layout", "VARCHAR DEFAULT 'grid'"),
                ("hide_header", "INTEGER DEFAULT 0"),
            ]:
                if col not in ds_cols:
                    try:
                        logging.info("[migrate] Adding ‘%s’ column to displaysettings", col)
                        conn.exec_driver_sql(f"ALTER TABLE displaysettings ADD COLUMN {col} {definition}")
                    except SQLAlchemyError as e:
                        logging.warning("[migrate] Could not add %s column: %s", col, e)
            row = conn.exec_driver_sql("SELECT id FROM displaysettings WHERE id=1").fetchone()
            if not row:
                conn.exec_driver_sql("INSERT INTO displaysettings (id, title, logo_image_id, accent_color, theme) VALUES (1, ‘What’’s on Tap’, NULL, ‘#ffb400’, ‘dark’)")

            conn.exec_driver_sql("CREATE TABLE IF NOT EXISTS storedimage (id INTEGER PRIMARY KEY, kind VARCHAR, ref_id INTEGER, content_type VARCHAR, data BLOB, created_at VARCHAR)")
            conn.commit()
    except (SQLAlchemyError, OSError) as exc:
        logging.warning(
            "Lightweight migration skipped or failed (%s): %s", type(exc).__name__, exc
        )


_lightweight_migrate()


def get_session():
    """FastAPI dependency yielding a database session (context-managed)."""
    with Session(engine) as session:
        yield session
