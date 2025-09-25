"""Database engine setup and lightweight runtime migrations."""

import os
import logging
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError

_db_path = os.getenv("DB_PATH", "/data/opentap.db")
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
except Exception as exc:
    logging.warning("[db] Could not import models pre-create_all: %s", exc)

SQLModel.metadata.create_all(engine)


def _lightweight_migrate():
    """Perform simple additive, idempotent schema adjustments.

    Ensures:
      * legacy ``image`` and new ``image_id`` columns for beer
      * displaysettings table (+ ``logo_image_id`` column) and singleton row
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
                if "image" not in existing_cols:
                    try:
                        logging.info("[migrate] Adding 'image' column to beer")
                        conn.exec_driver_sql("ALTER TABLE beer ADD COLUMN image VARCHAR")
                    except SQLAlchemyError as e:
                        logging.warning("[migrate] Could not add image column: %s", e)
                if "image_id" not in existing_cols:
                    try:
                        logging.info("[migrate] Adding 'image_id' column to beer")
                        conn.exec_driver_sql("ALTER TABLE beer ADD COLUMN image_id INTEGER")
                    except SQLAlchemyError as e:
                        logging.warning("[migrate] Could not add image_id column: %s", e)

            conn.exec_driver_sql("CREATE TABLE IF NOT EXISTS displaysettings (id INTEGER PRIMARY KEY, title VARCHAR, logo VARCHAR, logo_image_id INTEGER)")
            ds_cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(displaysettings);").fetchall()}
            if "logo_image_id" not in ds_cols:
                try:
                    logging.info("[migrate] Adding 'logo_image_id' column to displaysettings")
                    conn.exec_driver_sql("ALTER TABLE displaysettings ADD COLUMN logo_image_id INTEGER")
                except SQLAlchemyError as e:
                    logging.warning("[migrate] Could not add logo_image_id: %s", e)
            row = conn.exec_driver_sql("SELECT id FROM displaysettings WHERE id=1").fetchone()
            if not row:
                conn.exec_driver_sql("INSERT INTO displaysettings (id, title, logo, logo_image_id) VALUES (1, 'What’s on Tap', NULL, NULL)")

            conn.exec_driver_sql("CREATE TABLE IF NOT EXISTS storedimage (id INTEGER PRIMARY KEY, kind VARCHAR, ref_id INTEGER, content_type VARCHAR, data BLOB, created_at VARCHAR)")
    except (SQLAlchemyError, OSError) as exc:
        logging.warning(
            "Lightweight migration skipped or failed (%s): %s", type(exc).__name__, exc
        )


_lightweight_migrate()


def get_session():
    """FastAPI dependency yielding a database session (context-managed)."""
    with Session(engine) as session:
        yield session
