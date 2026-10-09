"""Gen26 crypto strategy zoo (protocol config/crypto_zoo_protocol.json, committed 160ed8d before any zoo return).
Stage 1: every configuration on DEV (BTC_OHLC and MULTI_CLOSE). Stages 2-3 (VAL, TEST) only for configurations that pass DEV."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import vector as VB  # noqa: E402
from qpl.data import coinmetrics as CM, crypto as CD  # noqa: E402
from qpl.htf import core as H  # noqa: E402
from qpl.research import crypto_factory as CF, factory as F, v6  # noqa: E402
from qpl.strategies import crypto as CS, crypto_zoo as Z  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROTO = "config/crypto_zoo_protocol.json"
COST = 7.5
PER = {"BTC": {"DEV": ("2015-01-01", "2019-12-31"), "VAL": ("2020-01-01", "2021-12-31"), "TEST": ("2022-01-01", "2023-12-31"), "USED_2024_26": ("2024-01-01", "2026-10-08")},
       "MULTI": {"DEV": ("2017-07-01", "2020-12-31"), "VAL": ("2021-01-01", "2022-12-31"), "TEST": ("2023-01-01", "2026-05-23")}}
SQ = np.sqrt(365)


def sh(x):
    x = x.dropna(); return float(x.mean() / x.std() * SQ) if len(x) > 30 and x.std() > 0 else 0.0


# ------------------------------------------------------------------ BTC engine (VB, actual funding)
btc = CD.btc_bars("1D").loc["2014-06-01":]
FUND, _ = CF.btc_funding()


def btc_daily(sig: pd.Series, cmult=1.0, fmult=1.0) -> pd.DataFrame:
    w = VB.vol_target(sig.reindex(btc.index).fillna(0), btc, 0.40, 30, 365.0)
    d = VB.daily(VB.run(btc, w, COST * cmult, FUND * fmult), at="realized")
    d.index = d.index.tz_localize(None)
    d["w"] = w.reindex(d.index.tz_localize("UTC")).to_numpy() if len(w) == len(d) else np.nan
    return d


BTC_BH = btc_daily(pd.Series(1.0, index=btc.index))["net"]

# ------------------------------------------------------------------ MULTI engine (Coin Metrics close, point-in-time top 10)
CMP = CM.load()
px = CMP["PriceUSD"].loc["2016-01-01":]; cap = CMP["CapMrktCurUSD"].reindex_like(px)
ret = px.pct_change(fill_method=None)
hist = px.notna().cumsum() >= 200
rank = cap.where(hist & px.notna()).rank(axis=1, ascending=False)
member = (rank <= 10)
vol = np.log(px).diff().rolling(30, min_periods=20).std() * SQ
MFUND_DAILY = 3e-4                                                          # 1 bp per 8h, paid by longs (baseline; alts lack data)


def multi_daily(sigs: pd.DataFrame, cmult=1.0, fmult=1.0) -> pd.DataFrame:
    w = (sigs.reindex_like(px).fillna(0) * (0.40 / vol)).clip(-1, 1).where(member, 0.0)
    n = member.sum(axis=1).replace(0, np.nan)
    w = w.div(n, axis=0).fillna(0)
    gross = (w.shift(1) * ret.fillna(0)).sum(axis=1)
    turn = w.diff().abs().sum(axis=1).fillna(0)
    cost = turn * COST * cmult / 1e4
    fund = (w.shift(1) * MFUND_DAILY * fmult).sum(axis=1)
    return pd.DataFrame({"gross": gross, "cost": cost, "funding": -fund, "net": gross - cost - fund, "turnover": turn})


MULTI_BH = multi_daily(pd.DataFrame(1.0, index=px.index, columns=px.columns))["net"]


def per_asset(fn, mode):
    return pd.DataFrame({a: Z.apply_mode(fn(px[a].dropna()), mode) for a in px.columns if px[a].notna().sum() > 250})


# ------------------------------------------------------------------ configs
C = []                                             # (sid, label, dataset, mode, maker)
for f, s in ([10, 50], [20, 100], [50, 200]): C += [("Z01_SMA_CROSS", f"{f}/{s}", m, (lambda c, f=f, s=s: Z.sma_cross(c, f, s))) for m in ("LS", "LO")]
for f, s in ([12, 26], [21, 55]): C += [("Z02_EMA_CROSS", f"{f}/{s}", m, (lambda c, f=f, s=s: Z.ema_cross(c, f, s))) for m in ("LS", "LO")]
for n in (50, 100, 200): C += [("Z03_PRICE_ABOVE_SMA", f"{n}", m, (lambda c, n=n: Z.price_above_sma(c, n))) for m in ("LS", "LO")]
for n in (14, 30, 90, 180): C += [("Z04_TSMOM", f"{n}", m, (lambda c, n=n: Z.tsmom(c, n))) for m in ("LS", "LO")]
for n in (20, 50): C += [("Z05_DONCHIAN_CLOSE", f"{n}", m, (lambda c, n=n: Z.donchian_close(c, n))) for m in ("LS", "LO")]
C += [("Z06_BOLLINGER_BREAKOUT", "20/2", m, (lambda c: Z.boll_breakout(c, 20, 2.0))) for m in ("LS", "LO")]
C += [("Z07_BOLLINGER_REVERSION", "20/2", m, (lambda c: Z.boll_reversion(c, 20, 2.0))) for m in ("LS", "LO")]
C += [("Z08_RSI_REVERSION", "14/30/70", m, (lambda c: Z.rsi_reversion(c, 14, 30, 70))) for m in ("LS", "LO")]
C += [("Z08_RSI_REVERSION", "2/10/90", m, (lambda c: Z.rsi_reversion(c, 2, 10, 90))) for m in ("LS", "LO")]
C += [("Z09_RSI_MOMENTUM", "14/55/45", m, (lambda c: Z.rsi_momentum(c, 14, 55, 45))) for m in ("LS", "LO")]
C += [("Z10_MACD", "12/26/9", m, (lambda c: Z.macd(c, 12, 26, 9))) for m in ("LS", "LO")]
C += [("Z11_ZSCORE_REVERSION", "5/1.5", m, (lambda c: Z.zscore_reversion(c, 5, 1.5))) for m in ("LS", "LO")]
C += [("Z12_SHORT_BREAKOUT", "7/2", m, (lambda c: Z.short_breakout(c, 7, 2))) for m in ("LS", "LO")]
C += [("Z13_VOL_MANAGED_LONG", "30", "LO", (lambda c: Z.vol_managed_long(c, 30)))]
C += [("Z14_CT1_ENSEMBLE", "frozen", m, None) for m in ("LS", "LO")]
OHLC_ONLY = [("Z16_SUPERTREND", "10/3", m, (lambda d: Z.supertrend(d, 10, 3.0))) for m in ("LS", "LO")]
OHLC_ONLY += [("Z17_ICHIMOKU", "9/26/52", m, (lambda d: Z.ichimoku(d, 9, 26, 52))) for m in ("LS", "LO")]
OHLC_ONLY += [("Z18_HEIKIN_ASHI", "3", m, (lambda d: Z.heikin_ashi(d, 3))) for m in ("LS", "LO")]


def ct1_sig(c, mode):
    bars = pd.DataFrame({"open": c, "high": c, "low": c, "close": c})
    w = CS.trend_ensemble(bars, {"long_only": mode == "LO"})
    return np.sign(w) * w.abs().clip(upper=1) / 0.4 * 0.4          # already vol-targeted inside; used as a signal in [-1,1]


rows, series = [], {}


def record_row(ds, sid, label, mode, d, bh):
    a, z = PER[ds]["DEV"]
    x, y = d["net"].loc[a:z], bh.loc[a:z]
    beta = np.cov(x, y)[0, 1] / y.var() if y.var() > 0 else 0.0
    rows.append({"dataset": ds, "sid": sid, "label": label, "mode": mode, "dev_net": sh(x), "dev_gross": sh(d["gross"].loc[a:z]),
                 "dev_resid": sh(x - beta * y), "dev_beta": float(beta), "dev_turnover_pa": float(d["turnover"].loc[a:z].mean() * 365)})
    series[(ds, sid, label, mode)] = d


# BTC
for sid, label, mode, mk in C:
    if sid == "Z14_CT1_ENSEMBLE":
        s = CS.trend_ensemble(btc, {"long_only": mode == "LO"}) / 0.4                 # signal ~ w/target
        s = s.clip(-1, 1)
    else:
        s = Z.apply_mode(mk(btc.close), mode)
    record_row("BTC", sid, label, mode, btc_daily(s), BTC_BH)
for sid, label, mode, mk in OHLC_ONLY:
    record_row("BTC", sid, label, mode, btc_daily(Z.apply_mode(mk(btc), mode)), BTC_BH)
# BTC weekly-level breakout (risk-normalised MTM; rescaled to the same ex-post vol as BTC_BH for comparability of Sharpe only)
ev = [e for e in H.detect_events(btc[["open", "high", "low", "close"]], H.htf_frame(btc, "crypto"), "PW") if e.strategy == "A2_BO"]
tr = H.simulate(btc, ev, lambda p: 0.0015 * p, hold=5)
mtm = H.daily_mtm(btc, tr, lambda p: 0.0015 * p); mtm.index = mtm.index.tz_localize(None)
bo = pd.DataFrame({"net": mtm, "gross": H.daily_mtm(btc, tr, lambda p: 0.0).set_axis(mtm.index), "turnover": 0.0})
record_row("BTC", "Z20_WEEKLY_LEVEL_BREAKOUT", "frozen", "LS", bo, BTC_BH)
# ORB UTC on BTC 1h (00-04 UTC range, exit 24:00)
h1 = CD.btc_bars("1h").loc["2014-06-01":]
day = h1.index.normalize()
g = h1.groupby(day)
rng_hi = h1[h1.index.hour < 4].groupby(day[h1.index.hour < 4]).high.max(); rng_lo = h1[h1.index.hour < 4].groupby(day[h1.index.hour < 4]).low.min()
orb = []
for d0, grp in g:
    if d0 not in rng_hi.index: continue
    after = grp[grp.index.hour >= 4]
    if len(after) < 10: continue
    hi, lo = rng_hi[d0], rng_lo[d0]; pos = 0; entry = None
    for t, b in after.iterrows():
        if pos == 0 and b.close > hi: pos, entry = 1, b.close
        elif pos == 0 and b.close < lo: pos, entry = -1, b.close
    if pos != 0:
        r_ = pos * (after.close.iloc[-1] / entry - 1)
        orb.append((d0, r_ - 0.0015, r_))
orb = pd.DataFrame(orb, columns=["d", "net", "gross"]).set_index("d"); orb.index = orb.index.tz_localize(None)
orb = orb.reindex(BTC_BH.index).fillna(0); orb["turnover"] = 0.0
record_row("BTC", "Z19_ORB_UTC", "4/24", "LS", orb, BTC_BH)

# MULTI
for sid, label, mode, mk in C:
    if sid == "Z14_CT1_ENSEMBLE":
        sig = pd.DataFrame({a: ct1_sig(px[a].dropna(), mode).clip(-1, 1) for a in px.columns if px[a].notna().sum() > 250})
    elif sid == "Z13_VOL_MANAGED_LONG":
        sig = per_asset(mk, "LO")
    else:
        sig = per_asset(mk, mode)
    record_row("MULTI", sid, label, mode, multi_daily(sig), MULTI_BH)
for n in (30, 90):                                   # Z15 dual-momentum rotation (top 3 by n-day momentum, if > 0)
    mom = np.log(px).diff(n).where(member)
    top = mom.rank(axis=1, ascending=False) <= 3
    sig = (top & (mom > 0)).astype(float) * 10 / 3      # multi_daily divides by N (~10): this makes each held coin ~1/3 of the book
    record_row("MULTI", "Z15_DUAL_MOMENTUM_ROTATION", f"{n}", "LO", multi_daily(sig), MULTI_BH)

R = pd.DataFrame(rows)
R["n_configs_total"] = len(R)
# neighbour rule within (dataset, sid)
R["sib_pos_share"] = R.groupby(["dataset", "sid"]).dev_net.transform(lambda s: (s > 0).mean())
R["dev_pass"] = (R.dev_net >= 1.0) & (R.dev_resid >= 0.5) & (R.sib_pos_share >= 2 / 3)
out = {"n_configs": int(len(R)), "dev_table": R.round(3).to_dict("records"), "stages": {}}
for i, r in R[R.dev_pass].iterrows():
    key = (r.dataset, r.sid, r.label, r["mode"])
    d = series[key]; bh = BTC_BH if r.dataset == "BTC" else MULTI_BH
    st = {}
    for p in ("VAL", "TEST"):
        a, z = PER[r.dataset][p]; x, y = d["net"].loc[a:z], bh.loc[a:z]
        beta = np.cov(x, y)[0, 1] / y.var()
        st[p] = {"net": sh(x), "gross": sh(d["gross"].loc[a:z]), "resid": sh(x - beta * y)}
    st["val_pass"] = bool(st["VAL"]["net"] >= 0.8 and st["VAL"]["resid"] > 0.3)
    out["stages"]["|".join(key)] = st
pd.to_pickle(series, ROOT / "results/crypto_zoo_gen26_series.pkl")
(ROOT / "results/crypto_zoo_gen26.json").write_text(json.dumps(out, indent=1, default=float))
for k in R.itertuples():
    F.append({"kind": "experiment", "hypothesis_id": f"{k.sid}", "asset_class": "crypto", "stage": "gen26_DEV", "protocol": PROTO,
              "params": {"label": k.label, "mode": k.mode, "dataset": k.dataset}, "summary": {"dev_net": k.dev_net, "dev_resid": k.dev_resid}})
pd.set_option("display.width", 220)
print(R.sort_values("dev_net", ascending=False).round(2).to_string(index=False))
print(json.dumps(out["stages"], indent=1))
