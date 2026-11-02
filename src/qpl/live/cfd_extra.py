"""bf2.7 candidate (C1, user-approved 2026-11-02 as a SHADOW next to bf2.6; bf2.6 itself is unchanged): the v9.8 'relative crowding 6' and
'diversifier basket' sleeves as BrightFunded crypto CFDs (swap-free: no funding; cost per side = half the measured BrightFunded spread
+ 1.2 bp). Frozen hourly ledgers paper_trading/rc6cfd and paper_trading/basketcfd ('port' = sleeve P&L as a fraction of equity), ingested
by the hub as paper:rc6cfd / paper:basketcfd and combined with bf2.6 (without its carry sleeves) in the shadow
'bf27cand:honest_plus_rc6_basket'.

Data: READ-ONLY use of the v9.8 paper trader's live data folder (paper_trading/v98/data) as QPL_LIVE_PACK, with the cutoff at the end of the
last hour the v9.8 paper has already frozen (so only hours whose inputs the v9.8 run validated). Signals are the unchanged basket_live code;
positions for hour h use data known before h (the book's own convention).

    python -m qpl.live.cfd_extra            # one step (the hub job 'cfdx_paper' runs it every hour)"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
START = pd.Timestamp("2026-11-03 00:00")
OUT = {"rc6 CFD": ROOT / "paper_trading/rc6cfd", "basket CFD": ROOT / "paper_trading/basketcfd"}
V98 = ROOT / "paper_trading/v98"


def costs(coins) -> pd.Series:
    spec = pd.read_csv(sorted(glob.glob(str(ROOT / "research_data/firm_specs/BrightFunded*20261021*.csv")))[-1], encoding="latin1")
    meas = {s.split("/")[0].replace("XDG", "DOGE"): float(v) for s, v in zip(spec["symbol"], spec["spread_bp_median"]) if "/USD" in s}
    return pd.Series({c: (0.5 * meas[c] + 1.2) / 1e4 for c in coins})


def cfd_pnl(pos: pd.DataFrame, R: pd.DataFrame, cost: pd.Series) -> pd.Series:
    """hourly P&L of positions (held during hour h) on hourly returns (of hour h), turnover at cost per side; swap-free (no funding)"""
    p = pos.reindex(index=R.index, columns=R.columns).fillna(0.0)
    return (p * R).sum(axis=1) - p.diff().abs().fillna(p.abs()).mul(cost.reindex(R.columns), axis=1).sum(axis=1)


def sleeves(index: pd.DatetimeIndex) -> dict[str, pd.Series]:
    """both CFD sleeves on `index` (must start early enough for the basket's 2022-24 scaling, e.g. 2021-01-01)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import basket_live as BL
    from qpl.lab import binance_pack as B
    C6 = list(BL.C6); cost = costs(C6)
    R = B.panel("close", "1h", C6).pct_change(fill_method=None).reindex(index).fillna(0.0)
    rc = cfd_pnl(BL.rc_positions(index), R, cost)
    _, W = BL.basket(index)
    bw = sum(w.reindex(columns=C6).fillna(0.0) for w in W.values())
    days = bw.index.append(pd.DatetimeIndex([bw.index[-1] + pd.Timedelta(days=1)]))       # row d (decided at the close of d) is held on d + 1
    bpos = bw.reindex(days).shift(1).reindex(index.floor("D")).set_axis(index).fillna(0.0)
    return {"rc6 CFD": rc, "basket CFD": cfd_pnl(bpos, R, cost)}


def _compute(cutoff: pd.Timestamp, now: pd.Timestamp) -> dict:
    """child process (env QPL_LIVE_PACK / QPL_CUTOFF set before the loaders import): append every completed hour >= START up to cutoff."""
    last = cutoff - pd.Timedelta(hours=1)
    if last < START:
        return {"status": f"waiting: first hour {START}"}
    S = sleeves(pd.date_range("2021-01-01", last, freq="h"))
    res = {}
    for col, d in OUT.items():
        d.mkdir(parents=True, exist_ok=True); f = d / "ledger_hourly.csv"
        L = pd.read_csv(f) if f.exists() else pd.DataFrame(columns=["hour", col, "port", "computed_at", "lag_h", "late"])
        have = set(L["hour"].astype(str)); rows = []
        for h, v in S[col].loc[START:last].items():
            if str(h) in have:
                continue                                                 # frozen: an hour is written once
            lag = (now - (h + pd.Timedelta(hours=1))).total_seconds() / 3600
            rows.append({"hour": str(h), col: float(v), "port": float(v), "computed_at": str(now), "lag_h": round(lag, 3), "late": lag > 2})
        if rows:
            L = pd.concat([L, pd.DataFrame(rows)], ignore_index=True); tmp = f.with_suffix(".tmp"); L.to_csv(tmp, index=False); tmp.replace(f)
        res[col] = len(rows)
    return {"cutoff": str(cutoff), "hours_written": res}


def step(log=print) -> dict:
    led = V98 / "ledger_hourly.csv"
    if not led.exists() or not (V98 / "data").exists():
        return {"status": "waiting for the v9.8 paper run (paper_trading/v98/ledger_hourly.csv and data/)"}
    v98_last = pd.Timestamp(pd.read_csv(led, usecols=["hour"])["hour"].max())
    now = pd.Timestamp.now(tz="UTC").tz_localize(None)
    cutoff = min(v98_last + pd.Timedelta(hours=1), now.floor("h"))
    env = dict(os.environ, QPL_LIVE_PACK=str(V98 / "data"), QPL_CUTOFF=str(cutoff), QPL_END=str(cutoff - pd.Timedelta(hours=1)), PYTHONPATH=str(ROOT / "src"))
    r = subprocess.run([sys.executable, "-m", "qpl.live.cfd_extra", "_compute", str(cutoff), str(now)], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        return {"status": "failed", "stderr": r.stderr[-1500:]}
    return json.loads(r.stdout.strip().splitlines()[-1])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "_compute":
        print(json.dumps(_compute(pd.Timestamp(sys.argv[2]), pd.Timestamp(sys.argv[3]))))
    else:
        print(json.dumps(step(), indent=1))
