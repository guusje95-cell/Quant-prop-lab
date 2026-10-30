"""Hypotheses and experiments. Every experiment is registered (config + periods + cost model + code / data version) BEFORE its
result is recorded; identical configurations are detected by their hash; the cumulative number of trials feeds the multiple-testing
adjustments. Results never overwrite an earlier experiment: a re-run is a new experiment."""
from __future__ import annotations

import json
import sqlite3
import subprocess

from qpl.hub.db import ROOT, audit, jhash, now, tx

HOLDOUT_FROM = "2025-01-01"          # project convention: 2022 development, 2023-24 validation, 2025-26 holdout (reused many times)


def code_version() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=10)
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
        return (r.stdout.strip() or "unknown") + ("+dirty" if dirty else "")
    except Exception:
        return "unknown"


def add_hypothesis(c: sqlite3.Connection, key: str, text: str, rationale: str = None, market: str = None, family: str = None,
                   source: str = None, registered_at: str = None, actor: str = "system") -> int:
    r = c.execute("SELECT id FROM hypotheses WHERE key=?", (key,)).fetchone()
    if r:
        return r["id"]
    with tx(c):
        cur = c.execute("INSERT INTO hypotheses (key, text, rationale, market, family, registered_at, source) VALUES (?,?,?,?,?,?,?)",
                        (key, text, rationale, market, family, registered_at or now(), source))
        audit(c, actor, "register_hypothesis", "hypotheses", cur.lastrowid, {"key": key})
    return cur.lastrowid


def register(c: sqlite3.Connection, key: str, kind: str, config: dict, *, title: str = None, hypothesis_key: str = None,
             version_id: int = None, periods: dict = None, cost_model: dict = None, seed: int = None, trials_added: int = 1,
             data_version: str = None, source: str = "hub", registered_at: str = None, status: str = "registered", actor: str = "system") -> int:
    """Register an experiment before running it. Returns its id (existing id when the key is already registered)."""
    r = c.execute("SELECT id FROM experiments WHERE key=?", (key,)).fetchone()
    if r:
        return r["id"]
    hid = None
    if hypothesis_key:
        h = c.execute("SELECT id FROM hypotheses WHERE key=?", (hypothesis_key,)).fetchone(); hid = h["id"] if h else None
    periods = periods or {}
    uses_holdout = int(any(str(v[1] if isinstance(v, (list, tuple)) else v) >= HOLDOUT_FROM for v in periods.values()) if periods else 0)
    h = jhash({"kind": kind, "config": config, "periods": periods, "cost_model": cost_model, "version_id": version_id})
    with tx(c):
        cur = c.execute("INSERT INTO experiments (key, hypothesis_id, version_id, kind, title, config, config_hash, code_version, data_version, periods, "
                        "cost_model, seed, registered_at, status, trials_added, uses_holdout, source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (key, hid, version_id, kind, title, json.dumps(config, default=str), h, code_version(), data_version, json.dumps(periods),
                         json.dumps(cost_model), seed, registered_at or now(), status, trials_added, uses_holdout, source))
        audit(c, actor, "register_experiment", "experiments", cur.lastrowid, {"key": key, "hash": h})
    return cur.lastrowid


def duplicates(c: sqlite3.Connection, config_hash: str) -> list[int]:
    return [r["id"] for r in c.execute("SELECT id FROM experiments WHERE config_hash=?", (config_hash,))]


def start(c: sqlite3.Connection, exp_id: int):
    with tx(c):
        c.execute("UPDATE experiments SET status='running', started_at=? WHERE id=? AND status IN ('registered','queued')", (now(), exp_id))


def finish(c: sqlite3.Connection, exp_id: int, metrics: dict, decision: str, reason: str, artifacts: dict = None, failed: bool = False,
           actor: str = "system"):
    r = c.execute("SELECT status FROM experiments WHERE id=?", (exp_id,)).fetchone()
    if r is None:
        raise KeyError(exp_id)
    if r["status"] in ("done", "failed", "cancelled"):
        raise ValueError(f"experiment {exp_id} already has a final result; register a new experiment for a re-run")
    with tx(c):
        c.execute("UPDATE experiments SET status=?, finished_at=?, metrics=?, decision=?, reason=?, artifacts=? WHERE id=?",
                  ("failed" if failed else "done", now(), json.dumps(metrics, default=str), decision, reason, json.dumps(artifacts, default=str), exp_id))
        audit(c, actor, "finish_experiment", "experiments", exp_id, {"decision": decision})


def trial_count(c: sqlite3.Connection, until: str = None) -> int:
    q = "SELECT COALESCE(SUM(trials_added),0) FROM experiments WHERE kind <> 'descriptive'"
    return int(c.execute(q + (" AND registered_at <= ?" if until else ""), ((until,) if until else ())).fetchone()[0])
