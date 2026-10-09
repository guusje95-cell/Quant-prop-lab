"""Crypto evaluation + recording (same registry/ledger as the futures factory)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..backtesting import vector as VB
from ..data import crypto as CD
from ..strategies import crypto as CS
from . import factory as F
from . import registry as R

SPLITS = {"train": ("2015-01-01", "2019-12-31"), "validation": ("2020-01-01", "2021-12-31"),
          "oos": ("2022-01-01", "2023-12-31"), "holdout": ("2024-01-01", "2026-10-09")}
DEV = ("train", "validation")
COSTS = {"perp_taker": 7.0, "spot_taker": 15.0}     # bps per unit turnover (ASSUMPTION; see report)
BASELINE_FUNDING_8H = 0.0001                        # ASSUMPTION where no venue data exists


def btc_funding(index_start="2015-01-01", index_end="2026-10-09") -> tuple[pd.Series, pd.Series]:
    """Funding for a BTC perp: actual Binance 2020-2023 and 2025-08..2026-09; baseline elsewhere.
    Returns (rates, is_actual flag)."""
    grid = pd.date_range(index_start, index_end, freq="8h", tz="UTC")
    s = pd.Series(BASELINE_FUNDING_8H, index=grid)
    actual = pd.Series(False, index=grid)
    a = CD.funding_binance_2020_2024("BTC")
    rec = CD.funding_recent("binance")
    rec = rec[rec.venue_symbol == "BTCUSDT"].set_index("settlement_ts")["rate_raw"]
    rec.index = rec.index.floor("h")
    for src in (a, rec):
        src = src[~src.index.duplicated()]
        common = s.index.intersection(src.index)
        s.loc[common] = src.loc[common].to_numpy()
        actual.loc[common] = True
    return s, actual


def evaluate(hyp: F.Hypothesis, signal: str, params: dict, rule: str = "1D", periods=DEV, cost="perp_taker",
             stage="screen", funding=True, record=True, w_override: pd.Series | None = None,
             label: str | None = None) -> dict:
    bars = CD.btc_bars(rule).loc["2014-06-01":]
    w = w_override if w_override is not None else CS.SIGNALS[signal](bars, params)
    f, _ = btc_funding() if funding else (None, None)
    res = VB.run(bars, w, COSTS[cost], f, perp=funding)
    d = VB.daily(res)
    bh = VB.daily(VB.run(bars, CS.buy_hold_vt(bars, {"target_vol": params.get("target_vol", 0.4)}), COSTS[cost], f, perp=funding))
    out = {"periods": {}}
    for p in periods:
        a, b = SPLITS[p]
        x = d.loc[a:b]
        y = bh.loc[a:b]
        st = VB.stats(x["net"])
        st.update({"gross_sharpe": VB.stats(x["gross"])["sharpe"], "cost_ann": float(x["cost"].sum() / max(len(x), 1) * 365),
                   "funding_ann": float(x["funding"].sum() / max(len(x), 1) * 365), "turnover_ann": float(x["turnover"].sum() / max(len(x), 1) * 365),
                   "corr_with_buyhold": float(x["net"].corr(y["net"])) if x["net"].std() > 0 else None,
                   "buyhold_vt_sharpe": VB.stats(y["net"])["sharpe"],
                   "by_year": {int(k): round(float(v), 4) for k, v in x["net"].groupby(x.index.year).sum().items()},
                   "share_time_long": float((res["w"].loc[a:b] > 0).mean()), "share_time_short": float((res["w"].loc[a:b] < 0).mean())})
        # residual vs buy & hold (beta-adjusted alpha)
        if x["net"].std() > 0 and y["net"].std() > 0:
            beta = np.cov(x["net"], y["net"])[0, 1] / y["net"].var()
            resid = x["net"] - beta * y["net"]
            st["beta_to_buyhold"] = float(beta)
            st["residual_sharpe"] = VB.stats(resid)["sharpe"]
        out["periods"][p] = st
    if record:
        meta = dict(generation=10, family=hyp.family, hypothesis_id=hyp.id, strategy=label or signal, instrument="BTCUSD (Bitstamp spot price; perp funding model)",
                    data_source="bitstamp_1m@edbab56 + funding", timeframe=rule, params=params, stage=stage, period=",".join(periods),
                    train_period=str(SPLITS["train"]), validation_period=str(SPLITS["validation"]), oos_period=str(SPLITS["oos"]),
                    metrics=out, decision="info", reason=f"v4 crypto; cost={cost}; funding={'actual+baseline' if funding else 'none'}")
        rid = R.record(**meta)
        F.append({"kind": "experiment", "registry_id": rid, "hypothesis_id": hyp.id, "asset_class": "crypto", "signal": label or signal,
                  "params": params, "rule": rule, "cost_bps": COSTS[cost], "periods": list(periods), "stage": stage,
                  "summary": {p: {k: v.get(k) for k in ("sharpe", "gross_sharpe", "residual_sharpe", "max_dd", "turnover_ann")} for p, v in out["periods"].items()}})
    return out
