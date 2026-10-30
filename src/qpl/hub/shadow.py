"""Shadow paper accounts: per-strategy and alternative-portfolio paper accounts derived EXACTLY from a running paper trader's frozen
hourly ledger (per-sleeve unit P&L and the book's effective sleeve weights; port = sum of weight x sleeve P&L, checked to 1e-16).

No extra market data or execution is needed for the sleeve and reweighted kinds, so a shadow is real paper evidence: the same
hours, the same fills and costs as the source run, combined differently. Kinds:
  sleeve        one sleeve alone, scaled to a volatility target with its BACKTEST daily sd (fixed in advance, no look-ahead)
  reweighted    the source book with per-sleeve multipliers on its own weights (e.g. ridge x0, Weiss x2)
  custom        fixed weights on the unit sleeve P&L
  rule          the source book with a rule-based multiplier (registered rules below; they use only data known before the hour)
Every shadow records when it was DEFINED: hours before that are a retroactive replay (shown separately), hours after it are forward
paper evidence. A shadow never changes the source paper trader."""
from __future__ import annotations

import json
import os
import sqlite3

import numpy as np
import pandas as pd

from qpl.hub import registry as RG
from qpl.hub.db import ROOT, audit, now, tx


def _btc_vol_regime(index: pd.DatetimeIndex, live_dir: str | None) -> pd.Series:
    """1.0 normally, 0.5 for the event short on days when BTC's 30-day vol (closes up to the previous day) is above its trailing
    365-day median (hub agenda item event_short_vol_regime)."""
    if live_dir and os.path.isdir(live_dir):
        os.environ.setdefault("QPL_LIVE_PACK", live_dir)
    from qpl.lab import binance_pack as B
    btc = B.k5("BTC").close.resample("1D").last(); vol = btc.pct_change().rolling(30).std()
    hi = (vol > vol.rolling(365, min_periods=180).median()).shift(1).fillna(False)
    return hi.reindex(index.floor("D")).set_axis(index).fillna(False).map({True: 0.5, False: 1.0})


RULES = {"event_short_vol_regime": {"sleeve": "listing short", "fn": _btc_vol_regime,
                                     "doc": "event short x0.5 when BTC 30-day vol is above its 1-year median (agenda item, flagged post hoc)"}}


def define(c: sqlite3.Connection, key: str, source: str, kind: str, spec: dict, capital: float = 200_000.0, risk: float = 1.5,
           description: str = "", actor: str = "user") -> int:
    if kind not in ("sleeve", "reweighted", "custom", "rule"):
        raise ValueError(kind)
    if kind == "rule" and spec.get("rule") not in RULES:
        raise ValueError(f"unknown rule; registered: {sorted(RULES)}")
    full = f"shadow:{key}"
    r = c.execute("SELECT id, config FROM paper_accounts WHERE key=?", (full,)).fetchone()
    cfg = {"shadow": True, "source": source, "kind": kind, "spec": spec, "risk": risk, "description": description, "defined_at": now()}
    if r:
        old = json.loads(r["config"])
        if {k: old.get(k) for k in ("source", "kind", "spec", "risk")} != {k: cfg[k] for k in ("source", "kind", "spec", "risk")}:
            raise ValueError(f"{full} exists with another definition: shadows are immutable, use a new key")
        return r["id"]
    with tx(c):
        i = c.execute("INSERT INTO paper_accounts (key, source_dir, initial_capital, status, config, created_at) VALUES (?,?,?,?,?,?)",
                      (full, f"derived from {source}", capital, "running", json.dumps(cfg), now())).lastrowid
        audit(c, actor, "define_shadow", "paper_accounts", i, cfg)
    if kind != "sleeve":
        RG.add_portfolio_version(c, f"shadow:{key}", "crypto_futures", "1", [source], {"kind": kind, "spec": spec}, state="paper_trading",
                                 notes=description, purpose="shadow paper account", actor=actor)
    return i


def _source_frames(c, source):
    a = c.execute("SELECT id, config FROM paper_accounts WHERE key=?", (source,)).fetchone()
    if not a:
        return None, None, None
    S = pd.read_sql_query("SELECT ts, sleeve, pnl, weight FROM paper_sleeve_pnl WHERE account_id=?", c, params=(a["id"],))
    if S.empty:
        return None, None, None
    S["ts"] = pd.to_datetime(S["ts"])
    return S.pivot(index="ts", columns="sleeve", values="pnl").fillna(0.0), S.pivot(index="ts", columns="sleeve", values="weight").ffill().fillna(0.0), a


def returns(c: sqlite3.Connection, key: str) -> pd.Series | None:
    """Unit-risk hourly returns of a shadow (before its own risk multiplier)."""
    cfg = json.loads(c.execute("SELECT config FROM paper_accounts WHERE key=?", (key,)).fetchone()["config"])
    P, W, a = _source_frames(c, cfg["source"])
    if P is None:
        return None
    k, s = cfg["kind"], cfg["spec"]
    if k == "sleeve":
        ver = cfg["source"].split(":", 1)[1]; sdf = ROOT / "results/paper_sleeve_sd.json"
        sd = json.loads(sdf.read_text()).get(ver, {}).get(s["sleeve"]) if sdf.exists() else None
        if not sd:
            raise ValueError(f"no backtest daily sd for sleeve {s['sleeve']} of {ver} (results/paper_sleeve_sd.json)")
        return P[s["sleeve"]] * (s.get("vol_target", 0.15) / (sd * np.sqrt(365)))
    if k == "reweighted":
        m = pd.Series({c_: s.get("multipliers", {}).get(c_, 1.0) for c_ in P.columns})
        return (P * W * m).sum(axis=1)
    if k == "custom":
        w = pd.Series(s["weights"]).reindex(P.columns).fillna(0.0)
        return (P * w).sum(axis=1)
    rule = RULES[s["rule"]]; mult = pd.DataFrame(1.0, index=P.index, columns=P.columns)
    mult[rule["sleeve"]] = rule["fn"](P.index, s.get("live_dir") or str(ROOT / "paper_trading" / cfg["source"].split(":", 1)[1] / "data"))
    return (P * W * mult).sum(axis=1)


def recompute(c: sqlite3.Connection, key: str | None = None) -> dict:
    out = {}
    keys = [key] if key else [r["key"] for r in c.execute("SELECT key FROM paper_accounts WHERE key LIKE 'shadow:%'")]
    for k in keys:
        row = c.execute("SELECT id, initial_capital, config FROM paper_accounts WHERE key=?", (k,)).fetchone(); cfg = json.loads(row["config"])
        try:
            r = returns(c, k)
        except Exception as e:                                         # noqa: BLE001 - one shadow must not block the others
            out[k] = {"error": str(e)}; continue
        if r is None or r.empty:
            out[k] = {"status": f"waiting for the source {cfg['source']} (no ledger ingested yet)"}; continue
        ret = r * cfg["risk"]; eq = row["initial_capital"] * (1 + ret).cumprod()
        defined = pd.Timestamp(cfg["defined_at"])
        with tx(c):
            c.execute("DELETE FROM paper_equity WHERE account_id=?", (row["id"],))          # derived data: rebuilt from the frozen source each time
            c.executemany("INSERT INTO paper_equity (account_id, ts, ret, equity, late, retro) VALUES (?,?,?,?,?,?)",
                          [(row["id"], str(t), float(x), float(e), 0, int(t < defined)) for t, x, e in zip(ret.index, ret, eq)])
            c.execute("UPDATE paper_accounts SET last_ingested_at=?, last_data_ts=? WHERE id=?", (now(), str(ret.index[-1]), row["id"]))
        out[k] = {"hours": len(ret), "forward_hours": int((ret.index >= defined).sum())}
    return out


def ensure_defaults(c: sqlite3.Connection, source: str = "paper:v98") -> list[int]:
    """Per-sleeve shadows of the v9.8 paper run plus two portfolio variants worth watching (defined once; immutable)."""
    from qpl.hub.ingest import SLEEVES_V98
    ids = []
    for s in SLEEVES_V98:
        ids.append(define(c, f"v98:{s.replace(' ', '_').replace('*', 'star').lower()}", source, "sleeve", {"sleeve": s, "vol_target": 0.15},
                          description=f"{s} alone at 15% vol (scaled with its backtest sd)", actor="system"))
    ids.append(define(c, "v98:event_vol_regime", source, "rule", {"rule": "event_short_vol_regime"},
                      description="candidate H1: v9.8 with the event short halved in high BTC vol (flagged post hoc)", actor="system"))
    ids.append(define(c, "v98:without_ridge", source, "reweighted", {"multipliers": {"ridge ML": 0.0}},
                      description="diagnostic: v9.8 without the ridge ML sleeve (leave-one-out was -0.04 in the backtest)", actor="system"))
    return ids
