"""Weekly paper report for the running books (config/paper_monitor.json): gate numbers, alerts, reconcile check, per-firm
accounts. Reads only the shared paper files; changes nothing in the paper runs.

    python scripts/paper_report.py            -> research/PAPER_REPORT.md (also printed)

Run after `git pull` of the user's shares (and, for the reconcile line, after `paper_v5.py reconcile` for each run)."""
import json
import subprocess
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
RUNS = ("v86", "bf26")
SD = json.loads((ROOT / "results/paper_sleeve_sd.json").read_text()) if (ROOT / "results/paper_sleeve_sd.json").exists() else {}


def one(ver):
    cfg = json.loads((ROOT / f"config/paper_{ver}.json").read_text()); fz = cfg["frozen"]; risk = float(fz["risk"]); acct = float(fz["account"])
    P = ROOT / "paper_trading" / ver
    if not (P / "ledger_hourly.csv").exists():
        return [f"## {ver}", "", "No shared paper files yet.", ""], []
    L = pd.read_csv(P / "ledger_hourly.csv", parse_dates=["hour"]); D = pd.read_csv(P / "daily.csv", parse_dates=["day"])
    bt = pd.read_parquet(ROOT / f"results/cache_{ver}_final.parquet")["portfolio"]
    btd = bt.groupby(bt.index.floor("D")).sum().loc["2023-01-01":] * risk
    n = len(D); r = D["ret"]; eq = D["equity"]
    dd = float((eq / eq.cummax().clip(lower=acct) - 1).min())
    z = float((r.mean() - btd.mean()) / (btd.std() / np.sqrt(n))) if n else np.nan
    late = float(L["late"].mean()); weiss = int((L.groupby(L["hour"].dt.floor("D"))["Weiss expiry"].apply(lambda x: (x != 0).any())).sum()) if "Weiss expiry" in L else 0
    stops = D.set_index("day")["daily_stop_hit"].astype(int)
    stop14 = int(stops.rolling("14D").sum().max()) if len(stops) else 0
    sleeves = [c for c in L.columns if f"w {c}" in L.columns]
    days = max(1.0, len(L) / 24)
    sl_rows, alerts = [], []
    for s in sleeves:
        cum = float(L[s].sum()); sd = SD.get(ver, {}).get(s)
        lim = -3 * sd * np.sqrt(days) if sd else None
        flag = lim is not None and cum < lim
        sl_rows.append(f"| {s} | {cum:+.2%} | {lim:+.2%} |" if lim is not None else f"| {s} | {cum:+.2%} | n/a |")
        if flag:
            alerts.append(f"{ver}: sleeve {s} below -3 sd ({cum:+.2%} < {lim:+.2%})")
    rec = "not run"
    if (P / "reconcile.csv").exists():
        R = pd.read_csv(P / "reconcile.csv")
        corr = float(R[["frozen", "recomputed"]].corr().iloc[0, 1]); cum = float((R["frozen"] - R["recomputed"]).sum() * risk)
        ok = (corr >= 0.99 or R["diff"].abs().max() < 1e-9) and abs(cum) <= 0.005
        rec = f"{len(R)} hours, correlation {corr:.4f}, cumulative difference {cum:+.3%} of the account -> **{'OK' if ok else 'INVESTIGATE'}**"
        if not ok:
            alerts.append(f"{ver}: reconcile not clean ({rec})")
    if dd < -0.08:
        alerts.append(f"{ver}: drawdown {dd:.2%} worse than -8%")
    if stop14 > 3:
        alerts.append(f"{ver}: {stop14} daily-stop days in a 14-day window")
    if late > 0.05:
        alerts.append(f"{ver}: late hours {late:.1%} > 5%")
    verdict = ("too early" if n < 56 or weiss < 2 else ("STOP" if z < -2 or dd < -0.12 else ("EXTEND" if z <= -1 else "GO (if Gen321 passed)")))
    if dd < -0.12 or (n >= 56 and z < -2):
        alerts.append(f"{ver}: STOP rule hit")
    lines = [f"## {ver} ({L['hour'].min():%Y-%m-%d %H:00} to {L['hour'].max():%Y-%m-%d %H:00} UTC, {len(L)} h, {n} days)", "",
             f"- Equity ${eq.iloc[-1]:,.0f} ({eq.iloc[-1] / acct - 1:+.2%}) at risk {risk}; max drawdown {dd:.2%}",
             f"- Daily mean {r.mean():+.3%} vs backtest {btd.mean():+.3%}: z = {z:+.2f} (one standard error of the mean is "
             f"{btd.std() / np.sqrt(n):.2%} a day at {n} days)",
             f"- Daily stops: {int(stops.sum())} (max {stop14} in 14 days); firm breaches: {int(D['firm_daily_breach'].sum())} daily / {int(D['firm_max_breach'].sum())} max",
             f"- Weiss expiries: {weiss}; late hours {late:.1%}; reconcile: {rec}",
             f"- Gate: **{verdict}**", "", "| Sleeve | Cumulative unit P&L | Alert level (-3 sd x sqrt(days)) |", "|---|---|---|"] + sl_rows + [""]
    return lines, alerts


def main():
    out, alerts = [f"# Paper report ({pd.Timestamp.now('UTC'):%Y-%m-%d %H:%M} UTC)", "",
                   "Simulation only. Rules: config/paper_monitor.json and the gates in config/paper_v86.json / paper_bf26.json. "
                   "The paper code is never changed because of these numbers.", ""], []
    for v in RUNS:
        l, a = one(v); out += l; alerts += a
    out[4:4] = ["## Alerts", ""] + ([f"- {a}" for a in alerts] if alerts else ["- none"]) + [""]
    if (ROOT / "paper_trading/v86/ledger_hourly.csv").exists():
        subprocess.run([sys.executable, str(ROOT / "scripts/paper_firms.py")], cwd=ROOT, capture_output=True)
        f = ROOT / "paper_trading/firms/status.md"
        if f.exists():
            out += ["## Per-firm accounts (v86 ledger)", ""] + f.read_text().splitlines()[4:] + [""]
    (ROOT / "research/PAPER_REPORT.md").write_text("\n".join(out) + "\n"); print("\n".join(out))


if __name__ == "__main__":
    main()
