"""Independent risk manager. It reads paper accounts (and, when present, the dry-run bot's state) and applies configured limits;
strategies cannot override it. Actions: warning, reduce (advisory scale for the bot), pause_entries / stop (writes the bot's kill
switch file bot_state/STOP), manual_review. Hysteresis: a triggered rule stays active until the value is back past `recover_below`.
Never increases risk; never places orders."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

from qpl.hub.db import ROOT, alert, audit, now, tx

DEFAULT_LIMITS = [  # scope, scope_key, rule, threshold, action, recover_below
    ("account", "*", "drawdown_from_peak", 0.08, "warning", 0.06),
    ("account", "*", "drawdown_from_peak", 0.12, "stop", 0.10),            # paper gate: STOP if paper drawdown worse than -12%
    ("account", "*", "daily_loss", 0.025, "pause_entries", 0.0),            # 50% of a 5% daily limit
    ("account", "*", "data_age_hours", 3.0, "pause_entries", 2.0),
    ("account", "*", "late_hours_share", 0.05, "warning", 0.03),
    ("bot", "*", "gross_exposure_x_initial", 1.9, "reduce", 1.7),          # HyroTrader funded cap 2x (kept at 1.9x)
]


def ensure_defaults(c: sqlite3.Connection):
    with tx(c):
        for sc, k, rule, th, act, rec in DEFAULT_LIMITS:
            c.execute("INSERT OR IGNORE INTO risk_limits (scope, scope_key, rule, threshold, action, recover_below) VALUES (?,?,?,?,?,?)",
                      (sc, k, rule, th, act, rec))


def measure_account(c: sqlite3.Connection, account_key: str) -> dict:
    a = c.execute("SELECT id FROM paper_accounts WHERE key=?", (account_key,)).fetchone()
    P = pd.read_sql_query("SELECT ts, ret, equity, late FROM paper_equity WHERE account_id=? ORDER BY ts", c, params=(a["id"],))
    if P.empty:
        return {}
    P["ts"] = pd.to_datetime(P["ts"]); eq = P["equity"]
    day = P[P["ts"].dt.floor("D") == P["ts"].iloc[-1].floor("D")]
    start_eq = float(eq.iloc[day.index[0] - 1]) if day.index[0] > 0 else float(eq.iloc[0] / (1 + P["ret"].iloc[0]))
    return {"drawdown_from_peak": float(1 - eq.iloc[-1] / eq.cummax().iloc[-1]), "daily_loss": max(0.0, float(1 - eq.iloc[-1] / start_eq)),
            "data_age_hours": (pd.Timestamp(now()) - P["ts"].iloc[-1]).total_seconds() / 3600, "late_hours_share": float(P["late"].fillna(0).mean())}


def evaluate(c: sqlite3.Connection, account_key: str, bot_dir: Path = ROOT / "bot_state", write_kill_switch: bool = True,
             active_only: bool = True) -> list[dict]:
    """Apply every enabled account limit to one paper account. Returns the events created. `active_only`: skip the data-age rule for
    accounts whose status is not 'running' (a finished paper run is not stale data)."""
    ensure_defaults(c); vals = measure_account(c, account_key); evs = []
    if not vals:
        return evs
    status = c.execute("SELECT status FROM paper_accounts WHERE key=?", (account_key,)).fetchone()["status"]
    lims = c.execute("SELECT * FROM risk_limits WHERE scope='account' AND enabled=1 AND scope_key IN ('*', ?) ORDER BY threshold", (account_key,)).fetchall()
    with tx(c):
        for L in lims:
            if L["rule"] == "data_age_hours" and active_only and status != "running":
                continue
            v = vals.get(L["rule"])
            if v is None:
                continue
            key = (L["scope"], account_key, f"{L['rule']}>{L['threshold']}")
            st = c.execute("SELECT active FROM risk_state WHERE scope=? AND scope_key=? AND rule=?", key).fetchone()
            active = bool(st["active"]) if st else False
            if not active and v > L["threshold"]:
                ev = {"rule": L["rule"], "value": v, "threshold": L["threshold"], "action": L["action"], "state": "triggered"}
                c.execute("INSERT OR REPLACE INTO risk_state VALUES (?,?,?,?,?)", (*key, 1, now()))
                c.execute("INSERT INTO risk_events (ts, scope, scope_key, rule, value, threshold, action, state, evidence) VALUES (?,?,?,?,?,?,?,?,?)",
                          (now(), "account", account_key, L["rule"], v, L["threshold"], L["action"], "triggered", json.dumps(vals)))
                alert(c, "critical" if L["action"] in ("stop", "pause_entries") else "warning", f"risk:{account_key}",
                      f"{L['rule']} {v:.4g} > {L['threshold']} -> {L['action']}", vals, dedup_key=f"risk:{account_key}:{key[2]}")
                if write_kill_switch and L["action"] == "stop" and account_key.endswith(":v98"):
                    bot_dir.mkdir(parents=True, exist_ok=True)
                    (bot_dir / "STOP").write_text(f"risk manager {now()}: {L['rule']} {v:.4g} > {L['threshold']}\n")
                    ev["kill_switch"] = str(bot_dir / "STOP")
                evs.append(ev)
            elif active and L["recover_below"] is not None and v <= L["recover_below"]:
                c.execute("INSERT OR REPLACE INTO risk_state VALUES (?,?,?,?,?)", (*key, 0, now()))
                c.execute("INSERT INTO risk_events (ts, scope, scope_key, rule, value, threshold, action, state, evidence) VALUES (?,?,?,?,?,?,?,?,?)",
                          (now(), "account", account_key, L["rule"], v, L["threshold"], L["action"], "recovered (manual review before resuming)", json.dumps(vals)))
                evs.append({"rule": L["rule"], "value": v, "state": "recovered"})
        audit(c, "risk", "evaluate", "paper_accounts", account_key, {"values": vals, "events": len(evs)})
    return evs


def portfolio_risk(sleeve_daily: pd.DataFrame, weights: pd.Series) -> dict:
    """Risk contributions (share of variance), correlation, and stress cases for a weighted set of daily sleeve returns."""
    X = sleeve_daily.fillna(0.0); w = weights.reindex(X.columns).fillna(0.0)
    C = X.cov(); tot = float(w @ C @ w); rc = (w * (C @ w)) / tot if tot > 0 else w * 0
    port = X @ w; base = float(port.mean() / port.std() * (365 ** 0.5))
    st = {}
    best = (X.mean() / X.std()).idxmax()
    p2 = X.drop(columns=best) @ w.drop(best); st[f"strongest sleeve ({best}) stops working (P&L = 0)"] = float(p2.mean() / p2.std() * 365 ** 0.5)
    hi = X.copy(); m = X.mean(); hi = (hi - m) * 1.0 + m
    corr_up = float(w @ (0.5 * C + 0.5 * pd.DataFrame(pd.Series(X.std()).values[:, None] * pd.Series(X.std()).values[None, :], index=C.index, columns=C.columns)) @ w)
    st["correlations move halfway to 1"] = float((port.mean()) / (corr_up ** 0.5) * 365 ** 0.5)
    st["all sleeves' mean halved (edge decay)"] = float((port.mean() / 2) / port.std() * 365 ** 0.5)
    worst = port.rolling(30).sum().min(); st["worst 30-day sum (unit book)"] = float(worst)
    return {"sharpe": base, "risk_contribution": rc.round(4).to_dict(), "correlation": X.corr().round(2).to_dict(), "stress": st}
