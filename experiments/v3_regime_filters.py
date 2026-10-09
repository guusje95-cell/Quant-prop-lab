"""Phase 4: regime / no-trade filters for H3 (NQ). Directions fitted on TRAIN only, frozen, then
evaluated on VALIDATION and OOS (OOS is semi-independent: H3 itself was evaluated there).
Each filter is compared with (1) unfiltered, (2) random removal of the same share of trades,
(3) half size on filtered-out trades instead of skipping."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import accounting as A  # noqa: E402
from qpl.features.intraday import asof_prior  # noqa: E402
from qpl.instruments import get  # noqa: E402
from qpl.research import factory as F, pipeline as P  # noqa: E402
from qpl.statistics import metrics as M  # noqa: E402
from qpl.strategies import v3_intraday as V  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FROZEN = dict(lookback=14, mult=1.25, trail="band_mean", check_min=60)
TR, VA, OO = P.SPLITS["train"], P.SPLITS["validation"], P.SPLITS["oos"]
hyp = F.Hypothesis("R_H3_FILTERS", "regime/no-trade", "Ex-ante regime features identify days on which H3 has negative expectancy.",
                   "Momentum needs trending, active markets; it fails in quiet mean-reverting tapes and after huge gaps.",
                   "No filter improves VALIDATION net expectancy per day AND reduces drawdown vs unfiltered after Holm over 5 filters; or random removal does as well.",
                   "15m NQ proxy", "5 filters, direction fitted on TRAIN median split", "unfiltered H3; random removal; half-size",
                   "VALIDATION Sharpe improvement > 0.2 and better than 95th pct of random removal")
hyp.register()


def sharpe(x):
    return float(x.mean() / x.std() * np.sqrt(252)) if x.std() > 0 else 0.0


def build(fut="NQ", proxy="US100", source="dukascopy", tf="M15", session=(570, 960), norm=True):
    ctx = P.context(source, proxy, tf, *session)
    days = P.trading_days(ctx); inst = get(fut)
    tr = P.backtest("noise_area", ctx, FROZEN, inst)
    u = P.usd(tr, inst, contracts=1, norm=norm)
    t = V.daily_rth_table(ctx)
    date = ctx["date"].to_numpy()
    rv = np.log(t.close).diff().rolling(20).std()
    eff = t.close.diff(10).abs() / t.close.diff().abs().rolling(10).sum()
    r20 = t.close.pct_change(20)
    f = pd.DataFrame({"rv20": asof_prior(rv, date), "eff10": asof_prior(eff, date), "ret20": asof_prior(r20, date),
                      "gap": np.abs(ctx.rth_open - ctx.prev_rth_close).to_numpy() / ctx.atr_d.to_numpy()}, index=ctx.index)
    # range since open up to the bar, normalized by ATR (known at the signal bar close)
    H, L = ctx.high.to_numpy(), ctx.low.to_numpy()
    rth = (ctx.rth & ctx.valid_day).to_numpy()
    g = pd.DataFrame({"d": date, "h": np.where(rth, H, np.nan), "l": np.where(rth, L, np.nan)})
    f["rng_atr"] = (g.groupby("d").h.cummax() - g.groupby("d").l.cummin()).to_numpy() / ctx.atr_d.to_numpy()
    sig_i = np.maximum(u.entry_i.to_numpy() - 1, 0)
    for k in f.columns:
        u[k] = f[k].to_numpy()[sig_i]
    u["aligned"] = np.sign(u["ret20"]) == u["dir"]
    return u, days


FILTERS = {"rv20": "rv20", "eff10": "eff10", "gap": "gap", "rng_atr": "rng_atr", "trend_align": "aligned"}


def main():
    u, days = build()
    tr_mask = (u.day >= TR[0]) & (u.day <= TR[1])
    out = {"unfiltered": {}, "filters": {}}
    base = A.daily_pnl(u, days)["pnl"]
    for per, (a, b) in {"train": TR, "validation": VA, "oos": OO}.items():
        out["unfiltered"][per] = {"sharpe": sharpe(base.loc[a:b]), "maxdd": M.summarize(base.loc[a:b])["max_dd_usd"],
                                  "trades": int(((u.day >= a) & (u.day <= b)).sum())}
    rng = np.random.default_rng(0)
    for name, col in FILTERS.items():
        if col == "aligned":
            keep_rule = lambda df: df["aligned"]  # noqa: E731
            med, direction = None, "aligned"
            ta = u[tr_mask]
            if ta.loc[ta["aligned"], "pnl_usd"].mean() < ta.loc[~ta["aligned"], "pnl_usd"].mean():
                keep_rule = lambda df: ~df["aligned"]  # noqa: E731
                direction = "counter"
        else:
            ta = u[tr_mask].dropna(subset=[col])
            med = float(ta[col].median())
            hi = ta.loc[ta[col] > med, "pnl_usd"].mean(); lo = ta.loc[ta[col] <= med, "pnl_usd"].mean()
            direction = "above" if hi > lo else "below"
            keep_rule = (lambda df, c=col, m=med: df[c] > m) if direction == "above" else (lambda df, c=col, m=med: df[c] <= m)
        keep = keep_rule(u).fillna(False).to_numpy(bool)
        kept = A.daily_pnl(u[keep], days)["pnl"]
        half = u.copy(); half.loc[~keep, "pnl_usd"] *= 0.5; half.loc[~keep, "mae_usd"] *= 0.5
        halfd = A.daily_pnl(half, days)["pnl"]
        res = {"direction": direction, "train_median": med, "share_kept_train": float(keep[tr_mask.to_numpy()].mean())}
        for per, (a, b) in {"train": TR, "validation": VA, "oos": OO}.items():
            pm = ((u.day >= a) & (u.day <= b)).to_numpy()
            rnd = []
            for _ in range(300):
                rk = rng.random(len(u)) < keep[pm].mean()
                rnd.append(sharpe(A.daily_pnl(u[pm & rk], days)["pnl"].loc[a:b]))
            res[per] = {"sharpe_filtered": sharpe(kept.loc[a:b]), "sharpe_half_size": sharpe(halfd.loc[a:b]),
                        "maxdd_filtered": M.summarize(kept.loc[a:b])["max_dd_usd"], "trades": int((keep & pm).sum()),
                        "random_removal_p95": float(np.percentile(rnd, 95)), "random_removal_median": float(np.median(rnd)),
                        "worst_day_filtered": float(kept.loc[a:b].min())}
        out["filters"][name] = res
        F.append({"kind": "experiment", "hypothesis_id": "R_H3_FILTERS", "filter": name, "summary": res})
    (ROOT / "results" / "v3_regime_filters.json").write_text(json.dumps(out, indent=1, default=float))
    return out


if __name__ == "__main__":
    o = main()
    print("unfiltered", o["unfiltered"])
    for k, v in o["filters"].items():
        print(k, v["direction"], "kept", round(v["share_kept_train"], 2),
              {p: (round(v[p]["sharpe_filtered"], 2), round(v[p]["sharpe_half_size"], 2), round(v[p]["random_removal_p95"], 2), v[p]["trades"]) for p in ("train", "validation", "oos")})
