"""Permanent experiment database (SQLite) - every backtest variant is recorded,
including failures, so multiple-testing penalties use the true trial count."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DB = ROOT / "research_database" / "experiments.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS experiments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT, generation INTEGER, family TEXT, hypothesis_id TEXT, strategy TEXT,
  instrument TEXT, data_source TEXT, timeframe TEXT, params TEXT, stage TEXT,
  period TEXT, train_period TEXT, validation_period TEXT, oos_period TEXT,
  code_version TEXT, data_version TEXT, metrics TEXT, stats TEXT, decision TEXT, reason TEXT
);
CREATE TABLE IF NOT EXISTS hypotheses (
  id TEXT PRIMARY KEY, family TEXT, generation INTEGER, doc TEXT, status TEXT, verdict TEXT
);
"""


def _conn() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.executescript(SCHEMA)
    return c


def code_version() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True).stdout.strip() or "uncommitted"
    except Exception:
        return "unknown"


def data_version() -> str:
    cfg = json.loads((ROOT / "config" / "data_sources.json").read_text())
    s = cfg["dukascopy_github"]["commit"][:10] + "/" + cfg["topstepx_github"]["commit"][:10]
    return s


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    try:
        import numpy as np
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, (np.integer,)):
            return int(o)
    except Exception:
        pass
    return o


def record(**kw) -> int:
    c = _conn()
    kw.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S"))
    kw.setdefault("code_version", code_version())
    kw.setdefault("data_version", data_version())
    for k in ("params", "metrics", "stats"):
        if k in kw and not isinstance(kw[k], str):
            kw[k] = json.dumps(_clean(kw[k]), default=str)
    cols = ",".join(kw)
    q = ",".join("?" * len(kw))
    cur = c.execute(f"INSERT INTO experiments ({cols}) VALUES ({q})", list(kw.values()))
    c.commit()
    rid = cur.lastrowid
    c.close()
    return rid


def register_hypothesis(hid: str, family: str, generation: int, doc: dict, status: str = "open") -> None:
    c = _conn()
    c.execute("INSERT OR REPLACE INTO hypotheses (id,family,generation,doc,status,verdict) VALUES (?,?,?,?,?,?)",
              (hid, family, generation, json.dumps(doc), status, None))
    c.commit(); c.close()


def set_verdict(hid: str, status: str, verdict: str) -> None:
    c = _conn()
    c.execute("UPDATE hypotheses SET status=?, verdict=? WHERE id=?", (status, verdict, hid))
    c.commit(); c.close()


def count(where: str = "1=1") -> int:
    c = _conn()
    n = c.execute(f"SELECT COUNT(*) FROM experiments WHERE {where}").fetchone()[0]
    c.close()
    return n


def query(sql: str):
    c = _conn()
    rows = c.execute(sql).fetchall()
    c.close()
    return rows


def params_hash(p: dict) -> str:
    return hashlib.sha1(json.dumps(p, sort_keys=True).encode()).hexdigest()[:10]
