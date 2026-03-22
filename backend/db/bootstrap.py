import os
import sqlite3
import threading

from config import DATABASE_PATH
from db.seed_db import seed_database

REQUIRED_TABLES = ("medicare_rates", "cci_edits", "state_laws")

_BOOTSTRAP_LOCK = threading.Lock()
_BOOTSTRAPPED_PATHS: set[str] = set()


def ensure_pricing_db_ready(db_path: str | None = None) -> str:
    target_path = os.path.abspath(db_path or DATABASE_PATH)

    with _BOOTSTRAP_LOCK:
        if target_path in _BOOTSTRAPPED_PATHS and _database_has_required_data(target_path):
            return target_path

        if not _database_has_required_data(target_path):
            seed_database(target_path)

        _BOOTSTRAPPED_PATHS.add(target_path)
        return target_path


def _database_has_required_data(db_path: str) -> bool:
    if not os.path.exists(db_path):
        return False

    try:
        conn = sqlite3.connect(db_path)
        existing_tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        if any(table not in existing_tables for table in REQUIRED_TABLES):
            return False

        medicare_rates_count = conn.execute(
            "SELECT COUNT(*) FROM medicare_rates"
        ).fetchone()[0]
        return medicare_rates_count > 0
    except sqlite3.Error:
        return False
    finally:
        try:
            conn.close()
        except UnboundLocalError:
            pass
