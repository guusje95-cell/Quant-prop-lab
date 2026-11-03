"""Failure-mode safety for the dry-run / future live bots (2026-11-03, task 'bot safety tests'). Used by runner_v99, venue_mt5,
venue_propr and runner_dailyflat (the frozen v9.8 runner keeps its own helpers).

  load_state / save_state   atomic write (tmp + replace) with a .bak copy; a corrupt or truncated state.json falls back to the .bak
                            (and is reported) instead of stopping the bot in an endless error loop
  read_json                 a missing / truncated book or targets file returns None instead of raising
  sanitize_targets          non-finite targets (NaN / inf from a data glitch) are dropped (=> the coin is closed, the safe side) and reported
  gross_cap                 hard sanity cap on gross notional (a bug that blows a target up cannot open a giant position)
  stale_flatten_due         a book older than MAX_STALE_HOURS while positions are open => flatten (positions are never left unmanaged)
  heartbeat                 status.json with the last pass time, action and error, for the hub / weekly report"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import pandas as pd

MAX_STALE_HOURS = 6.0


def save_state(d: Path, s: dict):
    d = Path(d); d.mkdir(parents=True, exist_ok=True); f = d / "state.json"; tmp = d / "state.json.tmp"
    tmp.write_text(json.dumps(s, indent=1, default=str))
    if f.exists():
        try:
            json.loads(f.read_text()); os.replace(f, d / "state.json.bak")             # keep the last good state
        except Exception:                                                           # noqa: BLE001 - corrupt current file: do not keep it
            pass
    os.replace(tmp, f)


def load_state(d: Path) -> dict:
    d = Path(d)
    for name in ("state.json", "state.json.bak"):
        f = d / name
        if f.exists():
            try:
                s = json.loads(f.read_text())
                if name.endswith(".bak"):
                    s["_recovered_from_backup"] = True
                return s
            except Exception:                                                       # noqa: BLE001 - try the backup
                continue
    return {"_state_missing_or_corrupt": (d / "state.json").exists()}


def read_json(p: Path) -> dict | None:
    try:
        return json.loads(Path(p).read_text())
    except Exception:                                                               # noqa: BLE001 - missing / truncated / being written
        return None


def sanitize_targets(t: dict) -> tuple[dict, list]:
    good, bad = {}, []
    for c, v in (t or {}).items():
        try:
            f = float(v)
        except (TypeError, ValueError):
            bad.append(c); continue
        if math.isfinite(f):
            good[c] = f
        else:
            bad.append(c)
    return good, bad


def gross_cap(t: dict, cap_usd: float) -> tuple[dict, bool]:
    g = sum(abs(v) for v in t.values())
    if cap_usd <= 0 or g <= cap_usd:
        return dict(t), False
    k = cap_usd / g
    return {c: v * k for c, v in t.items()}, True


def stale_flatten_due(made_at_utc: str | None, now: pd.Timestamp, has_positions: bool, max_hours: float = MAX_STALE_HOURS) -> bool:
    if not has_positions:
        return False
    if not made_at_utc:
        return True
    now = now.tz_convert("UTC").tz_localize(None) if now.tzinfo else now
    return (now - pd.Timestamp(made_at_utc)).total_seconds() / 3600 > max_hours


def heartbeat(d: Path, res: dict | None = None, error: str | None = None):
    d = Path(d); d.mkdir(parents=True, exist_ok=True)
    f = d / "status.json"; old = read_json(f) or {}
    now = str(pd.Timestamp.now(tz="UTC").tz_localize(None).floor("s"))
    s = {"last_pass_utc": now, "ok": error is None, "action": (res or {}).get("action"), "error": error,
         "consecutive_errors": (old.get("consecutive_errors", 0) + 1) if error else 0,
         "last_ok_utc": now if error is None else old.get("last_ok_utc")}
    tmp = d / "status.json.tmp"; tmp.write_text(json.dumps(s, indent=1)); os.replace(tmp, f)
    return s
