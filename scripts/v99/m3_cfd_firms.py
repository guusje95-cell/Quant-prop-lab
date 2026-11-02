"""M3 (research/v99/m3_protocol.json): the bf2.7 CFD candidate per CFD prop firm (coins, commission, weekend rule).
python scripts/v99/m3_cfd_firms.py        (spawns one child per base variant; writes results/v99/m3_cfd_firms.json)"""
import json
import os
import subprocess
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
VARIANTS = {"BF": {"coins": None, "comm": 1.2}, "FN": {"coins": ["BTC", "ETH", "XRP", "ADA", "DOGE", "LINK", "LTC"], "alt": ["ADA", "DOGE", "LINK", "XLM", "XRP"], "comm": 4.0},
            "BF-c3": {"coins": None, "comm": 3.25}, "BF-c4": {"coins": None, "comm": 4.0}, "BF-c6": {"coins": None, "comm": 6.0}}


def child(name, out):
    os.environ["QPL_PAPER"] = "bf26"; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
    v = VARIANTS[name]
    import cfd_book as CB
    if v["coins"]:
        CB.CFD[:] = v["coins"]; CB.CFD_BASE[:] = v["coins"]; CB.SPREAD = pd.Series(10.0, index=CB.CFD)
        CB.ALT_CFD[:] = v["alt"]; CB.ALT_SPREAD = pd.Series(10.0, index=CB.ALT_CFD)
    CB.COMM = v["comm"]
    import paper_v5 as P
    P.set_env(pd.Timestamp("2026-09-30 12:00"), live=False)
    R = P.compute(); R["H"].to_parquet(out)


def extra(index, coins, comm):
    import basket_live as BL
    from qpl.lab import binance_pack as B
    from qpl.live import cfd_extra as X
    cost = X.costs(coins) - 1.2e-4 + comm * 1e-4
    six = BL.C6; BL.C6 = tuple(coins)
    try:
        pos = BL.rc_positions(index)
    finally:
        BL.C6 = six
    R = B.panel("close", "1h", list(coins)).pct_change(fill_method=None).reindex(index).fillna(0.0)
    rc = X.cfd_pnl(pos, R, cost)
    _, W = BL.basket(index); bw = sum(w.reindex(columns=["BTC", "ETH"]).fillna(0.0) for w in W.values())
    days = bw.index.append(pd.DatetimeIndex([bw.index[-1] + pd.Timedelta(days=1)]))
    bpos = bw.reindex(days).shift(1).reindex(index.floor("D")).set_axis(index).fillna(0.0)
    Rb = B.panel("close", "1h", ["BTC", "ETH"]).pct_change(fill_method=None).reindex(index).fillna(0.0)
    return rc, X.cfd_pnl(bpos, Rb, cost.reindex(["BTC", "ETH"]))


def main():
    sys.path.insert(0, str(ROOT / "scripts/v99")); sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
    tmp = ROOT / "results/v99/_m3"; tmp.mkdir(exist_ok=True)
    for n in VARIANTS:
        f = tmp / f"{n}.parquet"
        if not f.exists():
            subprocess.run([sys.executable, __file__, "_child", n, str(f)], check=True, cwd=ROOT, env=dict(os.environ, PYTHONPATH=str(ROOT / "src")))
    import c1_cfd_port as C
    out = {}; crypto_cols = None
    for n, v in VARIANTS.items():
        H = pd.read_parquet(tmp / f"{n}.parquet").drop(columns=["premium carry", "premium carry BF"], errors="ignore")
        coins6 = ["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE"] if not v["coins"] else [c for c in ["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE"] if c in v["coins"]]
        rc, bk = extra(pd.date_range("2021-01-01", H.index[-1], freq="h"), coins6, v["comm"])
        H = H.assign(**{"rc6 CFD": rc.reindex(H.index).fillna(0.0), "basket CFD": bk.reindex(H.index).fillna(0.0)})
        out[n] = C.full(C.book(H))
        if n == "FN":
            wk = H.index.to_series(); wd = wk.dt.weekday; hr = wk.dt.hour
            weekend = ((wd == 4) & (hr >= 21)) | (wd == 5) | ((wd == 6) & (hr < 21))
            Hw = H.copy(); cc = [c for c in Hw.columns if c != "vol-managed indices"]
            Hw.loc[weekend.values, cc] = 0.0; out["FN-wd"] = C.full(C.book(Hw))
        print(n, out[n], flush=True)
    ded = out["BF"][0] - 1.36
    res = {"backtest [2022-26, [2022, 2023-24, 2025-26]]": out, "planning (same deduction as BF -> 1.36)": {k: round(v[0] - ded, 2) for k, v in out.items()},
           "note": "BF here is rebuilt from paper_v5 (research pack); C1's 2.947 used the paper dump with the same code"}
    print(json.dumps(res, indent=1)); (ROOT / "results/v99/m3_cfd_firms.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "_child":
        child(sys.argv[2], sys.argv[3])
    else:
        main()
