"""Falsification attempts on the frozen H3 (NQ) candidate."""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import accounting as A, engine as E
from qpl.instruments import get
from qpl.research import pipeline as P
from qpl.strategies import index_intraday as SI

ROOT = Path(__file__).resolve().parents[1]
FROZEN = dict(lookback=14, mult=1.25, trail="band_mean", check_min=60)
DEV = ("2013-01-01", "2020-12-31"); OOS = ("2021-01-01", "2023-09-11")


def sharpe(x): return float(np.mean(x) / np.std(x) * np.sqrt(252)) if np.std(x) > 0 else 0.0


def main(fut="NQ", proxy="US100"):
    out = {}
    ctx = P.context("dukascopy", proxy, "M15"); days = P.trading_days(ctx); inst = get(fut)
    tr = P.backtest("noise_area", ctx, FROZEN, inst)
    u = P.usd(tr, inst, contracts=1)
    for name, (a, b) in {"dev": DEV, "oos": OOS}.items():
        uu = u[(u.day >= a) & (u.day <= b)]
        # 1) long vs short
        out[f"{name}_long_short"] = {s: {"n": int((uu.dir == d).sum()), "total": float(uu.pnl_usd[uu.dir == d].sum()),
                                         "exp": float(uu.pnl_usd[uu.dir == d].mean())} for s, d in (("long", 1), ("short", -1))}
        # 2) sign-flip permutation of gross trade P&L (net of costs), 5000 draws
        g = (uu.pnl_pts * inst.point_value).to_numpy()
        cost = (uu.cost_usd).to_numpy()
        actual = (g - cost).mean()
        rng = np.random.default_rng(0)
        flips = rng.choice([-1, 1], size=(5000, len(g)))
        perm = (flips * g - cost).mean(1)
        out[f"{name}_signflip_p"] = float(np.mean(perm >= actual))
        # 3) entry hour attribution
        eh = pd.DatetimeIndex(uu.entry_ts).tz_convert("America/New_York").hour
        out[f"{name}_by_entry_hour"] = {int(h): round(float(v), 1) for h, v in uu.groupby(eh).pnl_usd.sum().items()}
        # 4) exit reasons
        out[f"{name}_by_reason"] = {int(k): round(float(v), 1) for k, v in uu.groupby("reason").pnl_usd.sum().items()}
    # 5) execution perturbation: delay every entry and signal exit by one bar (15 min later)
    o = SI.noise_area(ctx, FROZEN)
    for f in ("entry_dir", "entry_type", "exit_sig"):
        arr = getattr(o, f); sh = np.zeros_like(arr); sh[1:] = arr[:-1]
        # never carry a signal across a day boundary
        d = ctx["date"].to_numpy(); same = np.r_[False, d[1:] == d[:-1]]
        sh[~same] = 0
        setattr(o, f, sh)
    o.risk_ref = np.r_[np.nan, o.risk_ref[:-1]]; o.stop_dist = np.r_[np.nan, o.stop_dist[:-1]]
    tr2 = E.run(ctx, o, SI.rth_session(ctx), inst.tick_size, 0)
    tr2["day"] = pd.DatetimeIndex(ctx["cme_date"].to_numpy()[tr2["exit_i"].to_numpy()])
    u2 = P.usd(tr2, inst, contracts=1)
    out["delay_1bar"] = {k: round(v["sharpe"], 2) for k, v in P.split_metrics(u2, days, {"dev": DEV, "oos": OOS}).items()}
    # 6) random extra slippage per trade: 0-4 ticks per side uniformly, 200 draws
    res = []
    rng = np.random.default_rng(1)
    for _ in range(200):
        extra = rng.uniform(0, 4, len(u)) * 2 * inst.tick_size * inst.point_value
        uu = u.copy(); uu["pnl_usd"] = uu["pnl_usd"] - extra
        d = A.daily_pnl(uu, days)
        res.append((sharpe(d.loc[DEV[0]:DEV[1], "pnl"]), sharpe(d.loc[OOS[0]:OOS[1], "pnl"])))
    res = np.array(res)
    out["random_extra_slip_0to4ticks"] = {"dev_p5": float(np.percentile(res[:, 0], 5)), "dev_p50": float(np.median(res[:, 0])),
                                          "oos_p5": float(np.percentile(res[:, 1], 5)), "oos_p50": float(np.median(res[:, 1]))}
    # 7) drop the best 10 days / best year
    d = A.daily_pnl(u, days)["pnl"]
    for name, (a, b) in {"dev": DEV, "oos": OOS}.items():
        x = d.loc[a:b]
        out[f"{name}_sharpe_drop_best10days"] = sharpe(x.drop(x.nlargest(10).index))
        yr = x.groupby(x.index.year).sum()
        out[f"{name}_sharpe_drop_best_year"] = sharpe(x[x.index.year != yr.idxmax()])
    (ROOT / "results" / f"h3_falsification_{fut}.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    for fut, px in (("NQ", "US100"), ("ES", "US500")):
        r = main(fut, px)
        print(fut, json.dumps(r, indent=0)[:3000])
