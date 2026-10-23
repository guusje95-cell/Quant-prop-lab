"""Per-firm paper accounts on the v8.6 paper ledger (Gen329). The book is identical at every crypto firm, so no extra paper process
is needed: this replays paper_trading/v86/ledger_hourly.csv (unit-risk hourly P&L, frozen as computed live) through each firm's rules
at the challenge risk Gen329 chose for it. Same accounting as paper_v5.account (daily stop at half the firm's daily limit, exit 10 bp
worse), plus a trailing max loss where the firm uses one. Simulation only.

    python scripts/paper_firms.py            -> paper_trading/firms/status.md and paper_trading/firms/<firm>_daily.csv
"""
import sys
from dataclasses import replace
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import propfirms as PF
P = PF.PRESETS; HY = P["HyroTrader Two-Step $200k"]
# (firm, challenge risk) - risk chosen on 2022-24 in Gen329; CFT uses 2.0 (also the planning-level choice)
FIRMS = {"hyrotrader": (HY, 2.0),
         "cft_2phase": (replace(P["Crypto Fund Trader 2-Phase $100k"], name="CFT 2-Phase 200k", account=200000, targets=(0.08, 0.04)), 2.0),
         "propr_2step_watch": (replace(HY, name="Propr 2-Step 200k", targets=(0.08, 0.05), daily_loss=0.05, max_loss=0.08, max_type="trailing",
                                       trailing_intraday=True), 1.0)}
OUT = ROOT / "paper_trading/firms"


def account(L, f, risk):
    acct = float(f.account); eq = hwm = acct; rows = []; dead = False
    for day, g in L.groupby(L["hour"].dt.floor("D")):
        start = eq; low = eq; stopped = False
        for r in g["port"].to_numpy():
            if stopped or dead:
                continue
            eq *= 1 + risk * r; low = min(low, eq)
            if f.max_type != "static":
                hwm = max(hwm, eq)
            if eq / start - 1 <= -0.5 * f.daily_loss:
                eq *= 1 - 0.001; low = min(low, eq); stopped = True
        floor_max = acct * (1 - f.max_loss) if f.max_type == "static" else hwm - acct * f.max_loss
        breach_d = low < start - f.daily_loss * (acct if f.daily_basis == "initial" else start); breach_m = low < floor_max
        dead = dead or breach_d or breach_m
        rows.append({"day": day.date(), "ret": eq / start - 1, "equity": round(eq, 2), "intraday_low": round(low, 2), "daily_stop_hit": stopped,
                     "firm_daily_breach": breach_d, "firm_max_breach": breach_m, "max_loss_floor": round(floor_max, 2),
                     "target_1_reached": eq >= acct * (1 + f.targets[0])})
    return pd.DataFrame(rows)


def main():
    L = pd.read_csv(ROOT / "paper_trading/v86/ledger_hourly.csv", parse_dates=["hour"])
    OUT.mkdir(parents=True, exist_ok=True)
    lines = [f"# Per-firm paper accounts on the v8.6 ledger ({L['hour'].min():%Y-%m-%d %H:00} to {L['hour'].max():%Y-%m-%d %H:00} UTC, {len(L)} h)", "",
             "Simulation only. Same hourly P&L for every firm; only the firm rules and the risk differ (Gen329).", "",
             "| Firm | Risk | Equity | Return | Distance to max-loss floor | Stops | Daily / max breaches | Target 1 |", "|---|---|---|---|---|---|---|---|"]
    for key, (f, risk) in FIRMS.items():
        D = account(L, f, risk); D.to_csv(OUT / f"{key}_daily.csv", index=False)
        e = D["equity"].iloc[-1]; a = f.account
        lines.append(f"| {f.name} | {risk} | ${e:,.0f} | {e / a - 1:+.2%} | {(e - D['max_loss_floor'].iloc[-1]) / a:.2%} of the account | "
                     f"{int(D['daily_stop_hit'].sum())} | {int(D['firm_daily_breach'].sum())} / {int(D['firm_max_breach'].sum())} | "
                     f"{f.targets[0]:.0%} {'reached' if D['target_1_reached'].any() else 'not yet'} |")
    (OUT / "status.md").write_text("\n".join(lines) + "\n"); print("\n".join(lines))


if __name__ == "__main__":
    main()
