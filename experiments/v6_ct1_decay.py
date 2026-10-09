"""V6: why did CT1 decay? Descriptive decomposition on already-USED crypto data (no new selection, no re-tuning).
Competing explanations examined:
  E1 costs/funding grew            -> gross vs net, cost & funding drag by period
  E2 trend persistence in BTC fell -> variance ratios, TSMOM predictive regressions, sign hit rates by period
  E3 short side broke              -> long vs short P&L by period
  E4 horizon shift                 -> per-leg Sharpe by period (fast vs slow)
  E5 vol regime / capped sizing    -> BTC realized vol, mean |w|, share of time at the cap, realized strategy vol
  E6 fewer big trends              -> P&L concentration in the largest moves; |drift|/vol of the market
  E7 selection shrinkage / noise   -> bootstrap test of the dev-vs-post difference; expected shrinkage from selection among variants
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import vector as VB  # noqa: E402
from qpl.data import crypto as CD  # noqa: E402
from qpl.research import crypto_factory as CF, factory as F  # noqa: E402
from qpl.statistics import tests as T  # noqa: E402
from qpl.strategies import crypto as CS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
P = {"TRAIN 2015-19": ("2015-01-01", "2019-12-31"), "VAL 2020-21": ("2020-01-01", "2021-12-31"),
     "OOS 2022-23": ("2022-01-01", "2023-12-31"), "HOLDOUT 2024-26": ("2024-01-01", "2026-10-08")}
b = CD.btc_bars("1D").loc["2014-06-01":"2026-10-08"]
fund, _ = CF.btc_funding()
w = CS.trend_ensemble(b, {})
res = VB.run(b, w, 7.0, fund)
d = VB.daily(res, at="realized")
r = np.log(b["close"]).diff()
out: dict = {"periods": {}}

legs = {f"tsmom{L}": CS.tsmom(b, {"lookback": L, "target_vol": 0.4}) for L in (20, 60, 120)}
legs.update({f"donch{n}": CS.donchian(b, {"n": n, "target_vol": 0.4}) for n in (20, 55)})
leg_d = {k: VB.daily(VB.run(b, v, 7.0, fund), at="realized")["net"] for k, v in legs.items()}
wl, ws = w.clip(lower=0), w.clip(upper=0)
long_d = VB.daily(VB.run(b, wl, 7.0, fund), at="realized")["net"]
short_d = VB.daily(VB.run(b, ws, 7.0, fund), at="realized")["net"]
bh = VB.daily(VB.run(b, CS.buy_hold_vt(b, {}), 7.0, fund), at="realized")["net"]


def vr(x: pd.Series, q: int) -> float:
    """Lo-MacKinlay variance ratio of daily log returns (overlapping q-sums)."""
    x = x.dropna()
    return float(x.rolling(q).sum().var() / (q * x.var()))


def tsmom_reg(x: pd.Series, L: int, h: int) -> dict:
    """Predictive power of the sign of the trailing L-day return for the next h-day return (non-overlapping h)."""
    past = x.rolling(L).sum()
    fut = x.shift(-h).rolling(h).sum().shift(-(h - 1)) if h > 1 else x.shift(-1)
    df = pd.DataFrame({"s": np.sign(past), "f": fut}).dropna().iloc[::h]
    pnl = df.s * df.f
    t, _ = T.newey_west_t(pnl.to_numpy(), lags=2)
    return {"mean_signed_ret_bp": float(pnl.mean() * 1e4), "hit": float((pnl > 0).mean()), "t": t, "n": int(len(df))}


for name, (a, z) in P.items():
    x = d.loc[a:z]
    rr = r.loc[a:z]
    ww = w.loc[a:z]
    btc_vol = float(rr.std() * np.sqrt(365))
    gross = VB.stats(x["gross"])["sharpe"]
    big = x["net"].abs().sort_values(ascending=False)
    top_share = float(x["net"].loc[big.index[: max(1, int(0.05 * len(big)))]].sum() / x["net"].sum()) if x["net"].sum() != 0 else None
    out["periods"][name] = {
        "net_sharpe": VB.stats(x["net"])["sharpe"], "gross_sharpe": gross,
        "ann_gross": float(x["gross"].mean() * 365), "ann_cost": float(x["cost"].mean() * 365), "ann_funding": float(x["funding"].mean() * 365),
        "turnover_ann": float(x["turnover"].mean() * 365),
        "long_leg_sharpe": VB.stats(long_d.loc[a:z])["sharpe"], "short_leg_sharpe": VB.stats(short_d.loc[a:z])["sharpe"],
        "long_leg_ann": float(long_d.loc[a:z].mean() * 365), "short_leg_ann": float(short_d.loc[a:z].mean() * 365),
        "legs_sharpe": {k: VB.stats(v.loc[a:z])["sharpe"] for k, v in leg_d.items()},
        "btc_vol": btc_vol, "btc_buyhold_vt_sharpe": VB.stats(bh.loc[a:z])["sharpe"],
        "btc_drift_over_vol": float(rr.mean() * 365 / btc_vol),
        "mean_abs_w": float(ww.abs().mean()), "share_w_at_cap": float((ww.abs() > 0.999).mean()),
        "realized_strategy_vol": float(x["net"].std() * np.sqrt(365)),
        "share_long": float((ww > 0).mean()), "share_short": float((ww < 0).mean()),
        "signal_flips_per_year": float((np.sign(ww).diff().abs() > 0).sum() / (len(ww) / 365)),
        "VR5": vr(rr, 5), "VR20": vr(rr, 20), "VR60": vr(rr, 60),
        "tsmom_pred": {f"L{L}_h{h}": tsmom_reg(rr, L, h) for L in (20, 60, 120) for h in (5, 20)},
        "top5pct_days_share_of_pnl": top_share,
    }

# E7: is the dev -> post difference distinguishable from noise? block bootstrap of the mean difference
dev, post = d["net"].loc["2015-01-01":"2021-12-31"].to_numpy(), d["net"].loc["2022-01-01":"2026-10-08"].to_numpy()
rng = np.random.default_rng(3)
i1 = T.stationary_bootstrap_indices(len(dev), 2000, 20, rng)
i2 = T.stationary_bootstrap_indices(len(post), 2000, 20, rng)
sh = lambda m: m.mean(axis=1) / m.std(axis=1) * np.sqrt(365)
diff = sh(dev[i1]) - sh(post[i2])
out["dev_vs_post"] = {"dev_sharpe": float(dev.mean() / dev.std() * np.sqrt(365)), "post_sharpe": float(post.mean() / post.std() * np.sqrt(365)),
                      "diff_ci95": [float(np.quantile(diff, 0.025)), float(np.quantile(diff, 0.975))], "P(diff<=0)": float(np.mean(diff <= 0))}
# expected shrinkage from selection: gen10 variants' TRAIN Sharpes -> how much does the best regress in VAL? (empirical)
g = pd.read_csv(ROOT / "results/v4_crypto_gen10.csv")
g = g[g.hid.isin(["C1_TSMOM", "C2_DONCHIAN"])]
out["selection_shrinkage_gen10_trend"] = {"mean_train": float(g.tr_sh.mean()), "mean_val": float(g.va_sh.mean()),
                                         "slope_val_on_train": float(np.polyfit(g.tr_sh, g.va_sh, 1)[0])}
# BTC structural: rolling 1-year variance ratio VR20 and rolling CT1 Sharpe (for the chart/report)
roll = pd.DataFrame({"ct1_sharpe_365d": d["net"].rolling(365).mean() / d["net"].rolling(365).std() * np.sqrt(365),
                     "btc_vr20_365d": r.rolling(365).apply(lambda s: np.nan if s.isna().any() else s.rolling(20).sum().var() / (20 * s.var()), raw=False)})
roll.loc["2015-06-01":].resample("ME").last().to_csv(ROOT / "results/v6_ct1_decay_rolling.csv")
(ROOT / "results/v6_ct1_decay.json").write_text(json.dumps(out, indent=1, default=float))
F.append({"kind": "analysis", "hypothesis_id": "CT1_TREND_ENSEMBLE", "stage": "v6_decay_diagnosis", "result_file": "results/v6_ct1_decay.json",
          "note": "descriptive, on already-USED data; no selection"})
tab = pd.DataFrame({k: {kk: (vv if not isinstance(vv, dict) else None) for kk, vv in v.items()} for k, v in out["periods"].items()})
pd.set_option("display.width", 200)
print(tab.dropna(how="all").round(3).to_string())
print(pd.DataFrame({k: v["legs_sharpe"] for k, v in out["periods"].items()}).round(2))
print(pd.DataFrame({k: {kk: round(vv["mean_signed_ret_bp"], 1) for kk, vv in v["tsmom_pred"].items()} for k, v in out["periods"].items()}))
print(pd.DataFrame({k: {kk: round(vv["t"], 2) for kk, vv in v["tsmom_pred"].items()} for k, v in out["periods"].items()}))
print(json.dumps({k: out[k] for k in ("dev_vs_post", "selection_shrinkage_gen10_trend")}, indent=1))
