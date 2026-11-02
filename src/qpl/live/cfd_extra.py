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
OUT = {"rc6 CFD": ROOT / "paper_trading/rc6cfd", "basket CFD": ROOT / "paper_trading/basketcfd",
       "trend 4h ens CFD": ROOT / "paper_trading/trendcfd", "alt kimchi ens CFD": ROOT / "paper_trading/altkcfd"}     # bf2.8 (C10) adds the last two
V98 = ROOT / "paper_trading/v98"


def costs(coins) -> pd.Series:
    spec = pd.read_csv(sorted(glob.glob(str(ROOT / "research_data/firm_specs/BrightFunded*20261021*.csv")))[-1], encoding="latin1")
    meas = {s.split("/")[0].replace("XDG", "DOGE"): float(v) for s, v in zip(spec["symbol"], spec["spread_bp_median"]) if "/USD" in s}
    return pd.Series({c: (0.5 * meas[c] + 1.2) / 1e4 for c in coins})


def cfd_pnl(pos: pd.DataFrame, R: pd.DataFrame, cost: pd.Series) -> pd.Series:
    """hourly P&L of positions (held during hour h) on hourly returns (of hour h), turnover at cost per side; swap-free (no funding)"""
    p = pos.reindex(index=R.index, columns=R.columns).fillna(0.0)
    return (p * R).sum(axis=1) - p.diff().abs().fillna(p.abs()).mul(cost.reindex(R.columns), axis=1).sum(axis=1)


def positions(index: pd.DatetimeIndex) -> dict[str, pd.DataFrame]:
    """hourly per-coin positions (fraction of equity at sleeve level) of both CFD sleeves, held during each hour of `index`
    (decided from data known before the hour; must start early enough for the basket's 2022-24 scaling, e.g. 2021-01-01)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import basket_live as BL
    C6 = list(BL.C6)
    _, W = BL.basket(index)
    bw = sum(w.reindex(columns=C6).fillna(0.0) for w in W.values())
    days = bw.index.append(pd.DatetimeIndex([bw.index[-1] + pd.Timedelta(days=1)]))       # row d (decided at the close of d) is held on d + 1
    bpos = bw.reindex(days).shift(1).reindex(index.floor("D")).set_axis(index).fillna(0.0)
    return {"rc6 CFD": BL.rc_positions(index).reindex(columns=C6).fillna(0.0), "basket CFD": bpos}


def sleeves(index: pd.DatetimeIndex, pos: dict | None = None) -> dict[str, pd.Series]:
    """both CFD sleeves' hourly P&L on `index`."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import basket_live as BL
    from qpl.lab import binance_pack as B
    C6 = list(BL.C6); cost = costs(C6)
    R = B.panel("close", "1h", C6).pct_change(fill_method=None).reindex(index).fillna(0.0)
    P = pos or positions(index)
    return {k: cfd_pnl(v.reindex(index), R, cost) for k, v in P.items()}


def ensembles(index: pd.DatetimeIndex) -> dict[str, pd.Series]:
    """bf2.8 (C10, user-approved shadow 2026-11-02): the Gen383 neighbourhood ensembles as BrightFunded CFD sleeves, exactly the C3 code:
    trend 4h = mean of Donchian 15 / 20 / 30 positions on the CFD coins (cfd_book costs); alt kimchi = mean of thresholds 0.75 / 1.0 / 1.25
    on the altcoin CFDs (measured spread + 1.2 bp); no funding."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import alt_kimchi as AK
    import cfd_book as CB
    import crypto_sleeves as CS
    from qpl.lab import binance_pack as B
    CB.measured_costs()
    R = CB.hourly_returns(index[-1]).reindex(index).fillna(0.0)
    tpos = sum(CS.trend4h(n_in=n, n_out=n // 2, positions=True)[1] for n in (15, 20, 30)) / 3
    trend = CB.sleeve_pnl(tpos.reindex(columns=CB.CFD).fillna(0.0), R)
    ws = [AK.weights(th=t) for t in (0.75, 1.0, 1.25)]; aw = sum(ws) / len(ws)
    ac = [c for c in aw.columns if c in CB.ALT_CFD]; aw = aw[ac]
    ar = B.panel("close", "1h", ac).pct_change(fill_method=None).reindex(index).fillna(0.0)
    ap = aw.reindex(aw.index.append(pd.DatetimeIndex([aw.index[-1] + pd.Timedelta(days=1)]))).shift(1)
    p_ = ap.reindex(index.floor("D")).set_axis(index).fillna(0.0)
    acost = pd.Series({c: CB.ALT_SPREAD[c] + CB.COMM for c in ac}) / 1e4
    altk = (p_ * ar).sum(axis=1) - p_.diff().abs().fillna(p_.abs()).mul(acost, axis=1).sum(axis=1)
    return {"trend 4h ens CFD": trend.reindex(index).fillna(0.0), "alt kimchi ens CFD": altk.reindex(index).fillna(0.0)}


def _compute(cutoff: pd.Timestamp, now: pd.Timestamp) -> dict:
    """child process (env QPL_LIVE_PACK / QPL_CUTOFF set before the loaders import): append every completed hour >= START up to cutoff."""
    last = cutoff - pd.Timedelta(hours=1)
    if last < START:
        return {"status": f"waiting: first hour {START}"}
    ix = pd.date_range("2021-01-01", cutoff, freq="h")                  # includes the running hour `cutoff` for its positions
    P = positions(ix); S = sleeves(ix, P); S.update(ensembles(ix))
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
        if col not in P:
            continue
        row = P[col].loc[cutoff]                                         # positions during the running hour (bf2.7 dry-run book)
        (d / "open_positions.json").write_text(json.dumps({"for_hour_utc": str(cutoff), "made_at_utc": str(now), "sleeve": col,
                                                           "positions": {c: round(float(v), 6) for c, v in row.items() if abs(v) > 1e-9}}, indent=1))
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
