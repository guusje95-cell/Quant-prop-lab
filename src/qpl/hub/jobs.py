"""Persistent job queue + scheduler (SQLite). Dedup: at most one queued / running / paused job per dedup_key. Retries with
exponential backoff; timeouts and dead workers are recovered from heartbeats; nothing is lost on a restart (state is in the DB).
Only job kinds registered in HANDLERS (qpl.hub.handlers) can run."""
from __future__ import annotations

import json
import sqlite3

import pandas as pd

from qpl.hub.db import alert, audit, now, tx


def _ts(minutes: float = 0) -> str:
    return (pd.Timestamp(now()) + pd.Timedelta(minutes=minutes)).isoformat()


def enqueue(c: sqlite3.Connection, kind: str, payload: dict | None = None, dedup_key: str | None = None, priority: int = 5,
            max_attempts: int = 3, timeout_s: int = 3600, delay_minutes: float = 0, schedule_name: str | None = None, actor: str = "system") -> int:
    from qpl.hub.handlers import HANDLERS
    if kind not in HANDLERS:
        raise ValueError(f"unknown job kind {kind}; allowed: {sorted(HANDLERS)}")
    try:
        with tx(c):
            i = c.execute("INSERT INTO jobs (kind, payload, dedup_key, priority, status, max_attempts, timeout_s, next_run_at, created_at, schedule_name) "
                          "VALUES (?,?,?,?,?,?,?,?,?,?)", (kind, json.dumps(payload or {}, default=str), dedup_key, priority, "queued", max_attempts, timeout_s,
                                                           _ts(delay_minutes), now(), schedule_name)).lastrowid
            audit(c, actor, "enqueue", "jobs", i, {"kind": kind, "dedup": dedup_key})
        return i
    except sqlite3.IntegrityError:
        r = c.execute("SELECT id FROM jobs WHERE dedup_key=? AND status IN ('queued','running','paused')", (dedup_key,)).fetchone()
        return r["id"]


def claim(c: sqlite3.Connection, worker: str) -> sqlite3.Row | None:
    with tx(c):
        r = c.execute("SELECT * FROM jobs WHERE status='queued' AND next_run_at<=? ORDER BY priority, next_run_at, id LIMIT 1", (now(),)).fetchone()
        if not r:
            return None
        c.execute("UPDATE jobs SET status='running', attempts=attempts+1, started_at=?, heartbeat_at=?, worker=? WHERE id=? AND status='queued'",
                  (now(), now(), worker, r["id"]))
        return c.execute("SELECT * FROM jobs WHERE id=?", (r["id"],)).fetchone()


def heartbeat(c: sqlite3.Connection, job_id: int):
    c.execute("UPDATE jobs SET heartbeat_at=? WHERE id=? AND status='running'", (now(), job_id))


def complete(c: sqlite3.Connection, job_id: int, result: dict):
    with tx(c):
        c.execute("UPDATE jobs SET status='done', finished_at=?, result=?, error=NULL WHERE id=?", (now(), json.dumps(result, default=str)[:500_000], job_id))
        audit(c, "worker", "job_done", "jobs", job_id, None)


def fail(c: sqlite3.Connection, job_id: int, error: str):
    r = c.execute("SELECT attempts, max_attempts, kind FROM jobs WHERE id=?", (job_id,)).fetchone()
    with tx(c):
        if r["attempts"] < r["max_attempts"]:
            c.execute("UPDATE jobs SET status='queued', next_run_at=?, error=?, worker=NULL WHERE id=?", (_ts(2 ** r["attempts"]), error[-4000:], job_id))
            audit(c, "worker", "job_retry", "jobs", job_id, {"attempt": r["attempts"], "error": error[-300:]})
        else:
            c.execute("UPDATE jobs SET status='failed', finished_at=?, error=? WHERE id=?", (now(), error[-4000:], job_id))
            audit(c, "worker", "job_failed", "jobs", job_id, {"error": error[-300:]})
            alert(c, "warning", "jobs", f"job {job_id} ({r['kind']}) failed after {r['attempts']} attempts: {error[-200:]}", dedup_key=f"jobfail:{job_id}")


def recover_stale(c: sqlite3.Connection, grace_s: int = 300) -> list[int]:
    """Running jobs whose heartbeat is older than their timeout + grace (worker died or hung) are failed-and-retried."""
    out = []
    for r in c.execute("SELECT id, heartbeat_at, timeout_s FROM jobs WHERE status='running'").fetchall():
        hb = pd.Timestamp(r["heartbeat_at"] or "1970-01-01")
        if (pd.Timestamp(now()) - hb).total_seconds() > r["timeout_s"] + grace_s:
            fail(c, r["id"], "recovered: no heartbeat (worker stopped or job hung)"); out.append(r["id"])
    return out


def set_status(c: sqlite3.Connection, job_id: int, status: str, actor: str = "user"):
    allowed = {"cancel": ("queued", "paused"), "pause": ("queued",), "resume": ("paused",)}
    new = {"cancel": "cancelled", "pause": "paused", "resume": "queued"}[status]
    with tx(c):
        n = c.execute(f"UPDATE jobs SET status=? WHERE id=? AND status IN ({','.join('?' * len(allowed[status]))})", (new, job_id, *allowed[status])).rowcount
        audit(c, actor, f"job_{status}", "jobs", job_id, {"changed": n})
    return n


# ---------------------------------------------------------------------------------------------------------------- scheduler
DEFAULT_SCHEDULES = [  # name, kind, payload, every_minutes, priority
    ("ingest", "ingest", {}, 60, 3), ("risk", "risk", {}, 60, 2), ("health", "health", {}, 360, 4), ("backup", "backup", {}, 1440, 5),
    ("prop_staleness", "prop_staleness", {}, 1440, 6), ("validate_book", "validate_book", {"book": "v98"}, 10080, 7),
    ("validate_futures", "validate_book", {"book": "futures"}, 10080, 7),
    ("daily_summary", "daily_summary", {}, 1440, 8), ("paper_engine", "paper_engine", {}, 15, 1), ("agent", "agent_step", {}, 720, 9), ("integrity", "data_integrity", {}, 1440, 6),
    ("hl_snapshot", "hl_snapshot", {}, 60, 5),
]


def ensure_schedules(c: sqlite3.Connection):
    with tx(c):
        for name, kind, payload, every, prio in DEFAULT_SCHEDULES:
            c.execute("INSERT OR IGNORE INTO schedules (name, kind, payload, every_minutes, enabled, priority) VALUES (?,?,?,?,?,?)",
                      (name, kind, json.dumps(payload), every, 1, prio))


def _quiet(q: str | None) -> bool:
    if not q:
        return False
    a, b = (int(x) for x in q.split("-")); h = pd.Timestamp(now()).hour
    return (a <= h < b) if a < b else (h >= a or h < b)


def tick(c: sqlite3.Connection) -> list[int]:
    """Enqueue every enabled schedule that is due (deduplicated by schedule name)."""
    out = []
    for s in c.execute("SELECT * FROM schedules WHERE enabled=1").fetchall():
        last = pd.Timestamp(s["last_enqueued_at"]) if s["last_enqueued_at"] else None
        if (last is None or (pd.Timestamp(now()) - last).total_seconds() >= s["every_minutes"] * 60) and not _quiet(s["quiet_hours"]):
            out.append(enqueue(c, s["kind"], json.loads(s["payload"]), dedup_key=f"schedule:{s['name']}", priority=s["priority"], schedule_name=s["name"]))
            with tx(c):
                c.execute("UPDATE schedules SET last_enqueued_at=? WHERE name=?", (now(), s["name"]))
    return out
