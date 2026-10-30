"""Hub database: one SQLite file (WAL), versioned SQL migrations, audit log, alerts, settings, backups with a restore check.

The database lives in `hub_data/hub.sqlite` (override with QPL_HUB_DB). It is local state (paper ingests, jobs, finance), not in git.
Every write that matters goes through `tx()` (one transaction) and leaves an audit row."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MIGRATIONS = Path(__file__).with_name("migrations")
FIXED_SETTINGS = {"live_trading_enabled": "false"}          # cannot be changed through the hub (no live adapter exists)
DEFAULT_SETTINGS = {"live_trading_enabled": "false", "base_currency": "USD", "max_concurrent_jobs": "1", "job_cpu_seconds_budget_per_day": "28800",
                    "research_max_trials_per_task": "12", "backup_keep": "14", "personal_currency": "EUR"}


def db_path() -> Path:
    return Path(os.environ.get("QPL_HUB_DB", ROOT / "hub_data" / "hub.sqlite"))


def now() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


def connect(path: Path | None = None) -> sqlite3.Connection:
    p = Path(path) if path else db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(p, timeout=30, isolation_level=None)       # autocommit; explicit BEGIN in tx()
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL"); c.execute("PRAGMA foreign_keys=ON"); c.execute("PRAGMA busy_timeout=30000")
    return c


@contextmanager
def tx(c: sqlite3.Connection):
    c.execute("BEGIN IMMEDIATE")
    try:
        yield c
        c.execute("COMMIT")
    except BaseException:
        c.execute("ROLLBACK")
        raise


def migrate(c: sqlite3.Connection) -> list[str]:
    """Apply every migrations/NNN_*.sql not applied yet (each in one transaction). Returns the applied names."""
    c.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TEXT NOT NULL, sha256 TEXT NOT NULL)")
    done = {r["name"]: r["sha256"] for r in c.execute("SELECT name, sha256 FROM schema_migrations")}
    applied = []
    for f in sorted(MIGRATIONS.glob("*.sql")):
        sql = f.read_text(); h = hashlib.sha256(sql.encode()).hexdigest()
        if f.name in done:
            if done[f.name] != h:
                raise RuntimeError(f"migration {f.name} changed after it was applied; add a new migration instead")
            continue
        c.execute("BEGIN IMMEDIATE")
        try:
            for stmt in _split(sql):
                c.execute(stmt)
            c.execute("INSERT INTO schema_migrations VALUES (?,?,?)", (f.name, now(), h))
            c.execute("COMMIT")
        except BaseException:
            c.execute("ROLLBACK")
            raise
        applied.append(f.name)
    with tx(c):
        for k, v in DEFAULT_SETTINGS.items():
            c.execute("INSERT OR IGNORE INTO settings VALUES (?,?,?)", (k, v, now()))
        for k, v in FIXED_SETTINGS.items():
            c.execute("UPDATE settings SET value=?, updated_at=? WHERE key=? AND value<>?", (v, now(), k, v))
    if applied:
        audit(c, "system", "migrate", "schema", None, {"applied": applied})
    return applied


def _split(sql: str) -> list[str]:
    """Split a migration into complete statements (sqlite3.complete_statement handles triggers' BEGIN ... END)."""
    out, cur = [], ""
    for line in sql.splitlines():
        if line.strip().startswith("--") or not line.strip():
            continue
        cur += line + "\n"
        if sqlite3.complete_statement(cur):
            out.append(cur.strip()); cur = ""
    if cur.strip():
        raise ValueError(f"incomplete SQL statement at the end of a migration: {cur[:80]}")
    return out


def init(path: Path | None = None) -> sqlite3.Connection:
    c = connect(path); migrate(c); return c


def audit(c: sqlite3.Connection, actor: str, action: str, entity: str | None, entity_id, details=None, correlation_id: str | None = None):
    c.execute("INSERT INTO audit_log (ts, actor, action, entity, entity_id, details, correlation_id) VALUES (?,?,?,?,?,?,?)",
              (now(), actor, action, entity, None if entity_id is None else str(entity_id), _js(details), correlation_id))


def alert(c: sqlite3.Connection, level: str, source: str, message: str, evidence=None, dedup_key: str | None = None) -> int | None:
    """Open an alert unless an unacknowledged one with the same dedup_key exists."""
    if dedup_key and c.execute("SELECT 1 FROM alerts WHERE dedup_key=? AND acknowledged_at IS NULL", (dedup_key,)).fetchone():
        return None
    cur = c.execute("INSERT INTO alerts (ts, level, source, message, evidence, dedup_key) VALUES (?,?,?,?,?,?)",
                    (now(), level, source, message, _js(evidence), dedup_key))
    return cur.lastrowid


def get_setting(c: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    r = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return r["value"] if r else default


def set_setting(c: sqlite3.Connection, key: str, value: str, actor: str = "user"):
    if key in FIXED_SETTINGS and str(value) != FIXED_SETTINGS[key]:
        raise PermissionError(f"{key} cannot be changed through the hub (live trading is not available)")
    with tx(c):
        c.execute("INSERT INTO settings VALUES (?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                  (key, str(value), now()))
        audit(c, actor, "set_setting", "settings", key, {"value": value})


def _js(x):
    return None if x is None else (x if isinstance(x, str) else json.dumps(x, default=str, sort_keys=True))


def jhash(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


# ---------------------------------------------------------------------------------------------------------------- backups
def backup(c: sqlite3.Connection, dest_dir: Path | None = None) -> dict:
    """Online backup (sqlite backup API) -> hub_data/backups/hub_<ts>.sqlite, then verify it by opening the copy, running
    integrity_check and comparing row counts. Keeps the newest `backup_keep` files."""
    d = Path(dest_dir) if dest_dir else db_path().parent / "backups"; d.mkdir(parents=True, exist_ok=True)
    f = d / f"hub_{time.strftime('%Y%m%d_%H%M%S')}.sqlite"
    dst = sqlite3.connect(f)
    c.backup(dst); dst.close()
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    res = verify_backup(c, f)
    with tx(c):
        c.execute("INSERT INTO backups (ts, path, bytes, sha256, verified_at, verify_result) VALUES (?,?,?,?,?,?)",
                  (now(), str(f), f.stat().st_size, sha, now(), json.dumps(res)))
        audit(c, "system", "backup", "backups", f.name, res)
    keep = int(get_setting(c, "backup_keep", "14"))
    for old in sorted(d.glob("hub_*.sqlite"))[:-keep]:
        old.unlink()
    return {"path": str(f), "sha256": sha, **res}


def verify_backup(c: sqlite3.Connection, f: Path) -> dict:
    b = sqlite3.connect(f)
    try:
        ok = b.execute("PRAGMA integrity_check").fetchone()[0]
        tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        diff = {}
        for t in tables:
            n1 = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            n2 = b.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] if b.execute("SELECT 1 FROM sqlite_master WHERE name=?", (t,)).fetchone() else -1
            if t not in ("audit_log", "backups") and n1 != n2:
                diff[t] = [n1, n2]
        return {"integrity": ok, "tables": len(tables), "row_count_differences": diff, "restorable": ok == "ok" and not diff}
    finally:
        b.close()


def restore(backup_file: Path, target: Path | None = None) -> Path:
    """Restore a backup to `target` (default: the live db path). The current file is kept as <name>.before_restore."""
    t = Path(target) if target else db_path()
    if t.exists():
        t.replace(t.with_suffix(".before_restore"))
    src = sqlite3.connect(backup_file); dst = sqlite3.connect(t); src.backup(dst); src.close(); dst.close()
    return t
