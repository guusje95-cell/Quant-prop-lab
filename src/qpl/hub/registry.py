"""Strategy registry: strategies, immutable versions (code reference + parameters, identified by a config hash) and a lifecycle
with recorded evidence. A version used in an experiment or a paper account can never change (database trigger); a change of code or
parameters is a new version."""
from __future__ import annotations

import json
import sqlite3

from qpl.hub.db import audit, jhash, now, tx

STATES = ("idea", "research", "backtesting", "validation", "paper_trading", "candidate", "approved", "rejected", "archived")
ALLOWED = {
    "idea": {"research", "rejected", "archived"},
    "research": {"backtesting", "rejected", "archived"},
    "backtesting": {"validation", "rejected", "archived", "research"},
    "validation": {"paper_trading", "candidate", "rejected", "archived", "research"},
    "paper_trading": {"candidate", "rejected", "archived", "validation"},
    "candidate": {"approved", "paper_trading", "rejected", "archived"},
    "approved": {"paper_trading", "candidate", "archived", "rejected"},
    "rejected": {"archived", "research"},
    "archived": set(),
}
SCOPES = ("paper", "prop_challenge", "prop_funded", "own_capital")      # what an approval is FOR; approving never enables live execution


def upsert_strategy(c: sqlite3.Connection, key: str, name: str, market: str, family: str = None, description: str = None,
                    hypothesis: str = None, actor: str = "system") -> int:
    r = c.execute("SELECT id FROM strategies WHERE key=?", (key,)).fetchone()
    if r:
        return r["id"]
    with tx(c):
        cur = c.execute("INSERT INTO strategies (key, name, market, family, description, hypothesis, created_at) VALUES (?,?,?,?,?,?,?)",
                        (key, name, market, family, description, hypothesis, now()))
        audit(c, actor, "create_strategy", "strategies", cur.lastrowid, {"key": key})
    return cur.lastrowid


def add_version(c: sqlite3.Connection, strategy_key: str, version: str, code_ref: str, params: dict, state: str = "research",
                notes: str = None, actor: str = "system") -> int:
    """Register a version. The same parameters + code reference return the existing version (idempotent); a different
    configuration under an existing version label is refused."""
    sid = c.execute("SELECT id FROM strategies WHERE key=?", (strategy_key,)).fetchone()
    if not sid:
        raise KeyError(f"unknown strategy {strategy_key}")
    h = jhash({"code_ref": code_ref, "params": params})
    ex = c.execute("SELECT id, version FROM strategy_versions WHERE strategy_id=? AND config_hash=?", (sid["id"], h)).fetchone()
    if ex:
        return ex["id"]
    if c.execute("SELECT 1 FROM strategy_versions WHERE strategy_id=? AND version=?", (sid["id"], version)).fetchone():
        raise ValueError(f"{strategy_key} {version} already exists with a different configuration; use a new version label")
    if state not in STATES:
        raise ValueError(state)
    with tx(c):
        cur = c.execute("INSERT INTO strategy_versions (strategy_id, version, code_ref, params, config_hash, state, notes, created_at) "
                        "VALUES (?,?,?,?,?,?,?,?)", (sid["id"], version, code_ref, json.dumps(params, sort_keys=True), h, state, notes, now()))
        c.execute("INSERT INTO lifecycle_events (version_id, from_state, to_state, reason, actor, ts) VALUES (?,?,?,?,?,?)",
                  (cur.lastrowid, None, state, "registered", actor, now()))
        audit(c, actor, "create_version", "strategy_versions", cur.lastrowid, {"strategy": strategy_key, "version": version, "hash": h})
    return cur.lastrowid


def transition(c: sqlite3.Connection, version_id: int, to_state: str, reason: str, evidence=None, actor: str = "user",
               use_scope: str = None) -> None:
    r = c.execute("SELECT state FROM strategy_versions WHERE id=?", (version_id,)).fetchone()
    if not r:
        raise KeyError(version_id)
    frm = r["state"]
    if to_state not in ALLOWED.get(frm, set()):
        raise ValueError(f"transition {frm} -> {to_state} is not allowed")
    if not reason or not reason.strip():
        raise ValueError("a reason is required for every lifecycle transition")
    if to_state == "approved" and use_scope not in SCOPES:
        raise ValueError(f"an approval needs a use scope, one of {SCOPES}")
    with tx(c):
        c.execute("UPDATE strategy_versions SET state=? WHERE id=?", (to_state, version_id))
        c.execute("INSERT INTO lifecycle_events (version_id, from_state, to_state, use_scope, reason, evidence, actor, ts) VALUES (?,?,?,?,?,?,?,?)",
                  (version_id, frm, to_state, use_scope, reason, json.dumps(evidence, default=str) if evidence is not None else None, actor, now()))
        audit(c, actor, "transition", "strategy_versions", version_id, {"from": frm, "to": to_state, "scope": use_scope, "reason": reason})


def version_id(c: sqlite3.Connection, strategy_key: str, version: str) -> int | None:
    r = c.execute("SELECT v.id FROM strategy_versions v JOIN strategies s ON s.id=v.strategy_id WHERE s.key=? AND v.version=?",
                  (strategy_key, version)).fetchone()
    return r["id"] if r else None


def add_portfolio_version(c: sqlite3.Connection, key: str, market: str, version: str, members: list, allocation_rule: dict,
                          rebalance_rule: dict = None, state: str = "research", notes: str = None, purpose: str = None, actor: str = "system") -> int:
    r = c.execute("SELECT id FROM portfolios WHERE key=?", (key,)).fetchone()
    with tx(c):
        pid = r["id"] if r else c.execute("INSERT INTO portfolios (key, market, purpose, created_at) VALUES (?,?,?,?)", (key, market, purpose, now())).lastrowid
        h = jhash({"members": members, "allocation": allocation_rule, "rebalance": rebalance_rule})
        ex = c.execute("SELECT id, config_hash FROM portfolio_versions WHERE portfolio_id=? AND version=?", (pid, version)).fetchone()
        if ex:
            if ex["config_hash"] != h:
                raise ValueError(f"portfolio {key} {version} exists with a different configuration")
            return ex["id"]
        cur = c.execute("INSERT INTO portfolio_versions (portfolio_id, version, members, allocation_rule, rebalance_rule, config_hash, state, notes, created_at) "
                        "VALUES (?,?,?,?,?,?,?,?,?)", (pid, version, json.dumps(members), json.dumps(allocation_rule), json.dumps(rebalance_rule),
                                                     h, state, notes, now()))
        audit(c, actor, "create_portfolio_version", "portfolio_versions", cur.lastrowid, {"portfolio": key, "version": version})
    return cur.lastrowid
