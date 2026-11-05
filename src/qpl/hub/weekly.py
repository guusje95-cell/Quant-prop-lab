"""Weekly monitoring report (2026-11-03): every paper account, shadow and dry-run bot in one place, so that a deviation from the
backtest or a sick bot is seen within a week, not at the paper gate.

  1. Paper accounts (frozen ledgers paper_trading/<ver>/ledger_hourly.csv): days, last data, cumulative and annualised return / Sharpe,
     and z = (live daily mean - backtest daily mean) / (backtest daily sd / sqrt(days)) against the account's research series
     (REFS). Status: OK (z >= -1), WATCH (-2 <= z < -1), ALERT (z < -2 or data older than the account's stale limit).
  2. Shadows (hub DB, forward hours only): days, cumulative return, Sharpe.
  3. Bots (bot_state_*): status.json (last pass age, consecutive errors), orders in the last 7 days (count, turnover, skipped /
     rejected, kill / stop / stale closes), gross exposure.
Writes paper_trading/reports/weekly_<date>.md (Dutch summary) and .json; the hub job 'weekly_report' runs it weekly and raises an
alert for every ALERT line. Read-only: it never changes a ledger, a state file or a bot.

    python -m qpl.hub.weekly"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
PT = ROOT / "paper_trading"
OUT = PT / "reports"
# account -> (research series of 'port' in the ledger's units, column, stale limit in hours, label)
REFS = {"v98": ("results/v98_oct_oos.parquet", "port", 6, "crypto v9.8 (paper)"),
        "bf26": ("results/bf26_paper_sleeves.parquet", "port", 6, "CFD bf2.6 (paper)"),
        "futures": (None, None, 96, "futures swing book (paper)"),
        "futuresdf2": (None, None, 96, "futures daily-flat equity book (paper, DF-1c)"),
        "futcx": (None, None, 96, "futures + CX (shadow ledger)"), "futcx4": (None, None, 96, "futures + CX4 (shadow ledger)"),
        "futcx5": (None, None, 96, "futures + CX4 + basket (shadow ledger)")}
FUT_REF = {"futures": (0.000271414, 0.003537979)}                  # config/paper_futures.json reference (2023-01..2026-09)


def _daily(s: pd.Series) -> pd.Series:
    return s.groupby(s.index.floor("D")).sum()


def _ref_stats(name: str) -> tuple[float, float] | None:
    if name in FUT_REF:
        return FUT_REF[name]
    f, col = REFS.get(name, (None, None, 0, ""))[:2]
    if f and (ROOT / f).exists():
        x = pd.read_parquet(ROOT / f)[col]; d = _daily(x).loc["2023-01-01":"2026-09-30"]
        return float(d.mean()), float(d.std())
    if name == "futuresdf2":
        try:
            import sys
            sys.path.insert(0, str(ROOT / "scripts")); import fbook
            Q = pd.read_parquet(ROOT / "results/v99/df1c_sleeves.parquet")
            b = fbook.build(Q).loc["2023-01-01":"2026-09-30"]; return float(b.mean()), float(b.std())
        except Exception:                                                   # noqa: BLE001
            return None
    if name.startswith("futcx"):
        try:
            from qpl.live import futures_cx as FX
            P = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet"); cx = pd.read_parquet(FX.PREFIX)["CX"]
            if name in ("futcx4", "futcx5"):
                cx = cx.add(pd.read_parquet(FX.PREFIX4)["legs"], fill_value=0.0)
            P["CX"] = cx.reindex(P.index).fillna(0.0)
            if name == "futcx5":
                P["CXB"] = pd.read_parquet(FX.PREFIX5)["CXB"].reindex(P.index).fillna(0.0)
            b = FX.book(P)[0].loc["2023-01-01":"2026-09-30"]; return float(b.mean()), float(b.std())
        except Exception:                                                   # noqa: BLE001
            return None
    return None


def attribution(d: Path, ref_file: str | None) -> list[dict]:
    """per-sleeve contribution (weight x sleeve P&L) over the paper period vs its expectation from the research series' 2023-26 mean
    (paper weights x backtest mean per hour; sd from the backtest hourly sd, no autocorrelation): which sleeve drives a deviation"""
    if not ref_file or not (ROOT / ref_file).exists():
        return []
    L = pd.read_csv(d / "ledger_hourly.csv"); R = pd.read_parquet(ROOT / ref_file).loc["2023-01-01":"2026-09-30"]; out = []
    for c in [c for c in L.columns if f"w {c}" in L.columns]:
        w, p = L[f"w {c}"].astype(float), L[c].astype(float); act = float((w * p).sum())
        if c not in R:
            continue
        m, sd1 = float(R[c].mean()), float(R[c].std()); exp = float((w * m).sum()); sd = float(np.sqrt((w ** 2).sum()) * sd1)
        out.append({"sleeve": c, "actual": round(act, 5), "expected": round(exp, 5), "z": round((act - exp) / sd, 2) if sd > 0 else None})
    return sorted(out, key=lambda x: x["actual"])


def paper_accounts(now: pd.Timestamp) -> list[dict]:
    rows = []
    for d in sorted(p for p in PT.iterdir() if p.is_dir() and (p / "ledger_hourly.csv").exists()):
        name = d.name
        if name not in REFS:
            continue
        L = pd.read_csv(d / "ledger_hourly.csv", usecols=lambda c: c in ("hour", "port"))
        if L.empty:
            continue
        s = pd.Series(L["port"].astype(float).to_numpy(), index=pd.to_datetime(L["hour"])).sort_index()
        dd = _daily(s); n = len(dd); last = s.index[-1]; age_h = (now - last).total_seconds() / 3600
        ref = _ref_stats(name)
        z = float((dd.mean() - ref[0]) / (ref[1] / np.sqrt(n))) if ref and n >= 5 and ref[1] > 0 else None
        ann = 365 if REFS[name][2] <= 6 else 252
        sh = float(dd.mean() / dd.std() * np.sqrt(ann)) if n >= 5 and dd.std() > 0 else None
        stale = age_h > REFS[name][2]
        status = "ALERT" if (stale or (z is not None and z < -2)) else "WATCH" if (z is not None and z < -1) else "OK"
        rows.append({"account": name, "label": REFS[name][3], "days": n, "last_data": str(last), "age_h": round(age_h, 1),
                     "cum": round(float((1 + s).prod() - 1), 4), "sharpe_live": None if sh is None else round(sh, 2),
                     "backtest_daily_mean": None if not ref else ref[0], "z": None if z is None else round(z, 2), "stale": bool(stale), "status": status,
                     "sleeves": attribution(d, REFS[name][0])})
    return rows


def shadows(now: pd.Timestamp, daily: dict | None = None) -> list[dict]:
    """per shadow: forward days, cum, Sharpe; fills `daily` (key -> daily return series) when given"""
    db = Path(os.environ.get("QPL_HUB_DB", ROOT / "hub_data" / "hub.sqlite"))
    if not db.exists():
        return []
    c = sqlite3.connect(db); c.row_factory = sqlite3.Row; out = []
    for a in c.execute("SELECT id, key, config FROM paper_accounts WHERE key LIKE 'shadow:%'"):
        E = pd.read_sql_query("SELECT ts, ret FROM paper_equity WHERE account_id=? AND retro=0 ORDER BY ts", c, params=(a["id"],))
        if E.empty:
            out.append({"shadow": a["key"], "forward_days": 0}); continue
        s = pd.Series(E["ret"].to_numpy(), index=pd.to_datetime(E["ts"])); dd = _daily(s)
        if daily is not None:
            daily[a["key"]] = dd
        out.append({"shadow": a["key"], "forward_days": len(dd), "cum": round(float((1 + s).prod() - 1), 4),
                    "sharpe": round(float(dd.mean() / dd.std() * np.sqrt(365)), 2) if len(dd) >= 5 and dd.std() > 0 else None,
                    "last": str(s.index[-1])})
    c.close(); return out


def bots(now: pd.Timestamp) -> list[dict]:
    out = []
    for d in sorted(ROOT.glob("bot_state*")):
        if not d.is_dir():
            continue
        st = {}
        try:
            st = json.loads((d / "status.json").read_text())
        except Exception:                                                   # noqa: BLE001 - older bots have no heartbeat yet
            pass
        state = {}
        try:
            state = json.loads((d / "state.json").read_text())
        except Exception:                                                   # noqa: BLE001
            pass
        r = {"bot": d.name, "last_pass": st.get("last_pass_utc"), "consecutive_errors": st.get("consecutive_errors"), "last_error": st.get("error"),
             "gross_usd": round(sum(abs(float(v)) for v in (state.get("positions") or {}).values())), "positions": len(state.get("positions") or {})}
        if st.get("last_pass_utc"):
            r["pass_age_min"] = round((now - pd.Timestamp(st["last_pass_utc"])).total_seconds() / 60, 1)
        f = d / "orders_log.csv"
        if f.exists():
            try:
                O = pd.read_csv(f); t = pd.to_datetime(O.get("time"), errors="coerce", utc=True).dt.tz_localize(None)
                w = O[t >= now - pd.Timedelta(days=7)]
                how = w.get("how", pd.Series(dtype=str)).astype(str); reason = w.get("reason", pd.Series(dtype=str)).astype(str)
                r.update(orders_7d=int(len(w)), turnover_7d_usd=round(float(w.get("filled_usd", w.get("usd", pd.Series(dtype=float))).abs().sum())),
                         skipped_7d=int(how.str.contains("skipped").sum()), rejected_7d=int(how.str.contains("REJECTED").sum()),
                         safety_closes_7d=int(reason.str.contains("kill|stop|stale|unreadable", regex=True).sum()))
            except Exception as e:                                          # noqa: BLE001
                r["orders_error"] = str(e)[:100]
        bad = (r.get("consecutive_errors") or 0) >= 3 or (r.get("pass_age_min") or 0) > 30 or (r.get("rejected_7d") or 0) > 0
        r["status"] = "ALERT" if bad else "OK" if st else "NO HEARTBEAT"
        out.append(r)
    return out


def _md(rep: dict) -> str:
    L = [f"# Weekrapport {rep['date']}", "", "Status: OK = binnen verwachting; WATCH = z tussen -2 en -1; ALERT = z < -2, data te oud, of bot met fouten.",
         "", "## Paper-accounts (vs backtest 2023-26)", "", "| account | dagen | laatste data | cum. | Sharpe live | z | status |", "|---|---|---|---|---|---|---|"]
    for a in rep["paper"]:
        L.append(f"| {a['label']} | {a['days']} | {a['last_data']} ({a['age_h']} u) | {a['cum']:+.2%} | {a['sharpe_live']} | {a['z']} | **{a['status']}** |")
    for a in rep["paper"]:
        if a.get("sleeves"):
            L += ["", f"Per sleeve, {a['label']} (bijdrage aan het account, vs verwachting):", "", "| sleeve | werkelijk | verwacht | z |", "|---|---|---|---|"]
            L += [f"| {x['sleeve']} | {x['actual']:+.3%} | {x['expected']:+.3%} | {x['z']} |" for x in a["sleeves"]]
    L += ["", "Let op: met weinig dagen zegt de Sharpe live bijna niets (1 standaardfout ~ 2 Sharpe bij 60 dagen); z is de eerlijke maat.",
          "", "## Schaduwen (alleen uren na definitie)", "", "| schaduw | dagen | cum. | Sharpe |", "|---|---|---|---|"]
    for s in rep["shadows"]:
        L.append(f"| {s['shadow']} | {s.get('forward_days')} | {s.get('cum', '')} | {s.get('sharpe', '')} |")
    if not rep["shadows"]:
        L.append("| (hub-database niet gevonden: draai dit op de PC met de hub) | | | |")
    L += ["", "## Bots (dry-run)", "", "| bot | laatste ronde | fouten op rij | orders 7d | omzet 7d | overgeslagen | geweigerd | veiligheids-sluitingen | status |",
          "|---|---|---|---|---|---|---|---|---|"]
    for b in rep["bots"]:
        L.append(f"| {b['bot']} | {b.get('last_pass')} ({b.get('pass_age_min')} min) | {b.get('consecutive_errors')} | {b.get('orders_7d', '')} | "
                 f"{b.get('turnover_7d_usd', '')} | {b.get('skipped_7d', '')} | {b.get('rejected_7d', '')} | {b.get('safety_closes_7d', '')} | **{b['status']}** |")
    if rep["alerts"]:
        L += ["", "## Actie nodig", ""] + [f"- {x}" for x in rep["alerts"]]
    return "\n".join(L) + "\n"


def build(now: pd.Timestamp | None = None, write: bool = True) -> dict:
    now = now or pd.Timestamp.now(tz="UTC").tz_localize(None)
    sd: dict = {}
    rep = {"date": str(now.date()), "made_at_utc": str(now.floor("s")), "paper": paper_accounts(now), "shadows": shadows(now, sd), "bots": bots(now)}
    rep["alerts"] = ([f"paper {a['account']}: {a['status']} (z {a['z']}, data {a['age_h']} u oud)" for a in rep["paper"] if a["status"] == "ALERT"]
                     + [f"bot {b['bot']}: {b.get('consecutive_errors')} fouten op rij, laatste ronde {b.get('pass_age_min')} min geleden, "
                        f"geweigerd {b.get('rejected_7d')}" for b in rep["bots"] if b["status"] == "ALERT"])
    if write:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f"weekly_{rep['date']}.json").write_text(json.dumps(rep, indent=1, default=str))
        (OUT / f"weekly_{rep['date']}.md").write_text(_md(rep))
        if sd:                                                                     # day-by-day shadow returns (the hub database stays local)
            pd.DataFrame(sd).sort_index().rename_axis("day").to_csv(OUT / "shadows_daily.csv", float_format="%.6g")
    return rep


if __name__ == "__main__":
    r = build(); print(_md(r))
