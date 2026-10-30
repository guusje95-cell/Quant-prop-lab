"""Strategy / paper-account health: paper vs backtest with statistical caution (minimum samples, z-scores instead of raw Sharpe on a
few days), per-sleeve alerts, operational checks (late hours, data freshness). A warning records evidence and suggests diagnostics;
it never retunes anything."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from qpl.hub.db import ROOT, alert, audit, now, tx

MIN_DAYS_FOR_SHARPE = 60          # below this a rolling Sharpe is noise; only z-scores and operational checks are reported


def paper_series(c: sqlite3.Connection, account_key: str) -> pd.DataFrame:
    a = c.execute("SELECT id FROM paper_accounts WHERE key=?", (account_key,)).fetchone()
    if not a:
        raise KeyError(account_key)
    df = pd.read_sql_query("SELECT ts, ret, equity, late FROM paper_equity WHERE account_id=? ORDER BY ts", c, params=(a["id"],))
    df["ts"] = pd.to_datetime(df["ts"]); return df.set_index("ts")


def backtest_series(version: str) -> pd.Series | None:
    f = ROOT / f"results/cache_{version}_final.parquet"
    if not f.exists():
        return None
    x = pd.read_parquet(f); s = x["portfolio"] if "portfolio" in x else x.iloc[:, 0]
    return s.groupby(s.index.floor("D")).sum()


def check_account(c: sqlite3.Connection, account_key: str, risk: float | None = None) -> dict:
    ver = account_key.split(":", 1)[1]
    P = paper_series(c, account_key)
    cfg = json.loads(c.execute("SELECT config FROM paper_accounts WHERE key=?", (account_key,)).fetchone()["config"] or "{}")
    risk = risk if risk is not None else float(cfg.get("risk", 1.0))
    rep = {"account": account_key, "hours": len(P), "checked_at": now(), "status": "ok", "findings": []}
    if P.empty:
        rep.update(status="no data"); return rep
    d = P["ret"].groupby(P.index.floor("D")).sum(); n = len(d)
    eq = P["equity"]; dd = float((eq / eq.cummax() - 1).min())
    rep.update(days=n, first=str(P.index[0]), last=str(P.index[-1]), total_return=float(eq.iloc[-1] / eq.iloc[0] * (1 + P["ret"].iloc[0]) ** -1 - 1) if len(eq) > 1 else 0.0,
               max_drawdown=dd, late_share=float(P["late"].fillna(0).mean()))
    bt = backtest_series(ver)
    if bt is not None:
        b = bt.loc["2023-01-01":] * risk; mu, sd = b.mean(), b.std()
        z = (d.mean() - mu) / (sd / np.sqrt(n)) if n > 0 and sd > 0 else None
        rep.update(backtest_daily_mean=float(mu), backtest_daily_sd=float(sd), paper_daily_mean=float(d.mean()), z_vs_backtest=float(z) if z is not None else None,
                   one_se_of_mean=float(sd / np.sqrt(n)))
        if z is not None and n >= 14 and z < -2:
            rep["findings"].append({"level": "warning", "what": f"paper mean is {z:.2f} standard errors below the backtest after {n} days"})
    else:
        rep["findings"].append({"level": "info", "what": f"no backtest cache results/cache_{ver}_final.parquet: deviation not measurable"})
    if n >= MIN_DAYS_FOR_SHARPE:
        rep["paper_sharpe"] = float(d.mean() / d.std() * np.sqrt(365))
    else:
        rep["paper_sharpe"] = None; rep["note"] = f"Sharpe not reported below {MIN_DAYS_FOR_SHARPE} days (one standard error of an annual Sharpe at {n} days is about {np.sqrt(365 / max(n, 1)):.1f})"
    if rep["late_share"] > 0.05:
        rep["findings"].append({"level": "warning", "what": f"{rep['late_share']:.1%} of hours computed late (> 5% gate)"})
    last = P.index[-1]; age_h = (pd.Timestamp(now()) - last).total_seconds() / 3600
    rep["data_age_hours"] = age_h
    if age_h > 6:
        rep["findings"].append({"level": "info", "what": f"latest ingested hour is {age_h:.0f} h old: the paper trader is stopped, or its results were not shared yet"})
    # per-sleeve: cumulative unit P&L against -3 sd x sqrt(days) of the sleeve's backtest daily sd (paper_report convention)
    a = c.execute("SELECT id FROM paper_accounts WHERE key=?", (account_key,)).fetchone()["id"]
    S = pd.read_sql_query("SELECT ts, sleeve, pnl FROM paper_sleeve_pnl WHERE account_id=?", c, params=(a,))
    sdf = ROOT / "results/paper_sleeve_sd.json"; sds = json.loads(sdf.read_text()).get(ver, {}) if sdf.exists() else {}
    if not S.empty:
        cum = S.groupby("sleeve")["pnl"].sum(); rep["sleeves"] = {}
        for s, v in cum.items():
            lim = -3 * sds[s] * np.sqrt(max(n, 1)) if s in sds else None
            rep["sleeves"][s] = {"cum_unit_pnl": float(v), "alert_level": lim}
            if lim is not None and v < lim:
                rep["findings"].append({"level": "warning", "what": f"sleeve {s} cumulative {v:.2%} below its alert level {lim:.2%}"})
    if any(f["level"] == "warning" for f in rep["findings"]):
        rep["status"] = "warning"
    with tx(c):
        for f in rep["findings"]:
            if f["level"] != "info":
                alert(c, f["level"], f"health:{account_key}", f["what"], {"account": account_key}, dedup_key=f"health:{account_key}:{f['what'][:60]}")
        audit(c, "health", "check_account", "paper_accounts", account_key, {"status": rep["status"], "n_findings": len(rep["findings"])})
    rep["diagnostics_if_warning"] = ["reconcile frozen vs recomputed hours (paper_v5.py reconcile)", "compare per-sleeve P&L with the backtest sleeve on the same hours",
                                     "check data feeds for the affected sleeves", "do NOT retune on the adverse period"]
    return rep
