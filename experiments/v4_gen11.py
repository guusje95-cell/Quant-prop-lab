"""V4 generation 11: funding contrarian, funding carry, calendar, funding regime filter for CT1, alt XS momentum.
Protocol frozen in config/gen11_protocol.json BEFORE this script was first run. Later stages are gated in code."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as ss

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import vector as VB  # noqa: E402
from qpl.data import crypto as CD  # noqa: E402
from qpl.research import crypto_factory as CF, factory as F, registry as R  # noqa: E402
from qpl.strategies import crypto as CS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT: dict = {}
PROTO = "config/gen11_protocol.json"


def resid(x: pd.Series, y: pd.Series) -> tuple[float, float]:
    x, y = x.align(y, join="inner")
    if y.var() == 0 or x.std() == 0:
        return 0.0, 0.0
    b = np.cov(x, y)[0, 1] / y.var()
    return float(VB.stats(x - b * y)["sharpe"]), float(b)


def summary(d: pd.Series, bh: pd.Series | None = None) -> dict:
    s = VB.stats(d)
    if bh is not None:
        s["residual_sharpe"], s["beta"] = resid(d, bh)
    s["by_year"] = {int(k): round(float(v), 4) for k, v in d.groupby(d.index.year).sum().items()}
    return s


def record(hyp, label, params, stage, metrics, verdict_hint="info"):
    rid = R.record(generation=11, family=hyp.family, hypothesis_id=hyp.id, strategy=label, instrument=metrics.get("_instrument", "crypto"),
                   data_source=metrics.get("_data", "see protocol"), timeframe=metrics.get("_tf", ""), params=params, stage=stage,
                   period=stage, train_period="see protocol", validation_period="", oos_period="", metrics=metrics,
                   decision=verdict_hint, reason="v4 gen11")
    F.append({"kind": "experiment", "registry_id": rid, "hypothesis_id": hyp.id, "asset_class": "crypto", "signal": label,
              "params": params, "stage": stage, "protocol": PROTO,
              "summary": {k: metrics.get(k) for k in ("sharpe", "residual_sharpe", "ann_ret", "max_dd")}})


def H(hid, fam, st, mech, fals, data, grid, base):
    h = F.Hypothesis(hid, fam, st, mech, fals, data, grid, base, PROTO, generation=11)
    h.register()
    return h


# ------------------------------------------------------------------ shared data
btc_d = CD.btc_bars("1D").loc["2014-06-01":]
btc_h = CD.btc_bars("1h").loc["2019-06-01":]
fund_all, fund_actual = CF.btc_funding()
f_btc_old = CD.funding_binance_2020_2024("BTC")
f_eth_old = CD.funding_binance_2020_2024("ETH")
rec = CD.funding_recent("binance")
rec = rec[rec.venue_symbol.str.endswith("USDT")].copy()
rec["ts"] = rec.settlement_ts.dt.floor("h")
bh_daily = VB.daily(VB.run(btc_d, CS.buy_hold_vt(btc_d, {}), 7.0, fund_all))["net"]


def perp_panel():
    """8h mark-price bars + funding per symbol (2025-08..2026-09)."""
    out = {}
    for sym, g in rec.groupby("venue_symbol"):
        g = g.drop_duplicates("ts").set_index("ts").sort_index()
        g = g[g.index.hour % 8 == 0]                         # 4h-interval symbols: keep the 8h grid for the price bars
        m = g["mark_price"].astype(float)
        bars = pd.DataFrame({"open": m, "high": m, "low": m, "close": m})
        fr = rec[(rec.venue_symbol == sym)].drop_duplicates("ts").set_index("ts")["rate_raw"].astype(float).sort_index()
        out[sym] = (bars, fr)
    return out


PANEL = perp_panel()

# ------------------------------------------------------------------ C6 funding contrarian
h6 = H("C6_FUNDING_CONTRARIAN", "crypto/funding", "Extreme funding prints predict reversal over 24-72h.",
       "Crowded leveraged positioning (high funding) unwinds; liquidation cascades.", "see protocol", "Bitstamp 1h + Binance funding",
       "q {0.9,0.95} x hold {24,72}h", "BTC buy&hold-VT")
c6 = {"train": {}}
for q in (0.90, 0.95):
    for hold in (24, 72):
        prm = {"q": q, "hold": hold, "lb_settlements": 270}
        w = CS.funding_contrarian(btc_h, prm, f_btc_old)
        d = VB.daily(VB.run(btc_h, w, 7.0, fund_all))["net"]
        m = summary(d.loc["2020-07-01":"2021-12-31"], bh_daily)
        c6["train"][json.dumps(prm)] = m
        record(h6, "funding_contrarian", prm, "gen11_C6_train", {**m, "_tf": "1h"})
best = max(c6["train"], key=lambda k: c6["train"][k]["sharpe"])
bm = c6["train"][best]
n_pos = sum(v["sharpe"] > 0 for v in c6["train"].values())
c6["train_pass"] = bool(bm["sharpe"] >= 0.5 and bm.get("residual_sharpe", 0) >= 0.3 and n_pos >= 3)
c6["best"] = best
if c6["train_pass"]:
    prm = json.loads(best)
    w = CS.funding_contrarian(btc_h, prm, f_btc_old)
    d = VB.daily(VB.run(btc_h, w, 7.0, fund_all))["net"]
    m = summary(d.loc["2022-01-01":"2023-12-31"], bh_daily); c6["oos"] = m
    record(h6, "funding_contrarian", prm, "gen11_C6_OOS_LOOK", {**m, "_tf": "1h"})
    c6["oos_pass"] = bool(m["sharpe"] >= 0.5 and m["residual_sharpe"] > 0)
    if c6["oos_pass"]:
        nets, bhs = {}, {}
        for sym, (bars, fr) in PANEL.items():
            w = CS.funding_contrarian(bars, prm, fr)
            nets[sym] = VB.daily(VB.run(bars, w, 7.0, fr))["net"]
            bhs[sym] = VB.daily(VB.run(bars, CS.buy_hold_vt(bars, {"vol_lb": 90}), 7.0, fr))["net"]
        p = pd.DataFrame(nets).fillna(0).mean(axis=1).loc["2025-11-20":"2026-09-20"]
        b = pd.DataFrame(bhs).fillna(0).mean(axis=1).loc["2025-11-20":"2026-09-20"]
        m = summary(p, b); c6["holdout"] = m
        c6["holdout_pass"] = bool(m["sharpe"] > 0 and m["residual_sharpe"] > 0)
        record(h6, "funding_contrarian", prm, "gen11_C6_HOLDOUT_LOOK", {**m, "_tf": "8h"})
OUT["C6"] = c6
v6 = ("REJECT" if not c6["train_pass"] else "EXPLORATORY" if not c6.get("oos_pass") else
      "VALIDATION_CANDIDATE" if not c6.get("holdout_pass") else "PAPER_TRADING_CANDIDATE")
F.decide(h6, v6, f"TRAIN best {bm['sharpe']:.2f} (resid {bm.get('residual_sharpe', 0):.2f}), {n_pos}/4 positive; "
         f"OOS {c6.get('oos', {}).get('sharpe', 'n/a')}; holdout {c6.get('holdout', {}).get('sharpe', 'n/a')}", {"protocol": PROTO})
OUT["C6"]["verdict"] = v6

# ------------------------------------------------------------------ C7 funding carry (basis NOT modelled)
h7 = H("C7_FUNDING_CARRY", "crypto/carry", "Delta-neutral spot-long/perp-short earns funding above costs and cash.",
       "Structural demand for leveraged long exposure pays a premium to liquidity providers (basis trade).",
       "net return on capital <= 4% in any period", "Binance funding", "tau {0, 5e-5}", "always-on carry and 4% cash")


def carry(f: pd.Series, tau: float | None) -> pd.Series:
    """Per-settlement return on capital (2x notional). pos decided with prints up to s, earns the NEXT print."""
    f = f.sort_index()
    on = pd.Series(1.0, index=f.index) if tau is None else (f.rolling(21, min_periods=21).mean() > tau).astype(float)
    pos = on.shift(1).fillna(0.0)
    cost = pos.diff().abs().fillna(pos.iloc[0]) * 22e-4
    return (pos * f - cost) / 2.0


def ann(x: pd.Series, per_year=3 * 365) -> dict:
    r = float(x.sum() / len(x) * per_year) if len(x) else 0.0
    return {"ann_ret_on_capital": r, "sharpe_settlement": float(x.mean() / x.std() * np.sqrt(per_year)) if x.std() > 0 else None,
            "worst_8h": float(x.min()) if len(x) else 0.0, "share_on": float((x != 0).mean()) if len(x) else 0.0}


c7 = {}
for tau in (None, 0.0, 5e-5):
    key = "always_on" if tau is None else f"tau={tau}"
    c7[key] = {}
    for nm, f in (("BTC", f_btc_old), ("ETH", f_eth_old)):
        r = carry(f, tau)
        c7[key][nm] = {"train": ann(r.loc["2020-01-01":"2021-12-31"]), "oos": ann(r.loc["2022-01-01":"2023-12-31"])}
    hold = []
    for sym, (_, fr) in PANEL.items():
        per_year = 365 * 24 / pd.Series(fr.index).diff().dt.total_seconds().div(3600).median()
        x = carry(fr, tau).loc["2025-08-21":"2026-09-20"]
        hold.append(ann(x, per_year)["ann_ret_on_capital"])
    c7[key]["holdout_21perps_mean_ann"] = float(np.mean(hold))
    c7[key]["holdout_21perps_share_above_4pct"] = float(np.mean(np.array(hold) > 0.04))
    record(h7, "carry", {"tau": tau}, "gen11_C7_all", {"_instrument": "BTC/ETH/21 perps", "carry": c7[key]})
ok = {k: all(v[a][p]["ann_ret_on_capital"] > 0.04 for a in ("BTC", "ETH") for p in ("train", "oos")) and v["holdout_21perps_mean_ann"] > 0.04
      for k, v in c7.items()}
c7["pass_by_rule"] = ok
v7 = "EXPLORATORY" if any(ok[k] for k in ok if k != "always_on") else "REJECT"
F.decide(h7, v7, f"Carry (basis/counterparty unmodelled; ceiling EXPLORATORY). pass by rule: {ok}", {"protocol": PROTO})
c7["verdict"] = v7
OUT["C7"] = c7

# ------------------------------------------------------------------ C8 calendar (hour-of-day / weekday)
h8 = H("C8_CALENDAR", "crypto/calendar", "BTC mean returns differ by UTC hour or weekday.", "Session overlaps, funding times, weekend liquidity.",
       "no Holm survivor in TRAIN", "Bitstamp 1h", "31 tests", "zero")
hb = CD.btc_bars("1h").loc["2015-01-01":"2019-12-31"]
r = np.log(hb["close"]).diff().dropna()
tests = []
for hr in range(24):
    x = (r * (r.index.hour == hr)).to_numpy()            # zero-filled series preserves time ordering for NW
    t = ss.ttest_1samp(r[r.index.hour == hr], 0.0)
    tests.append(("hour", hr, float(r[r.index.hour == hr].mean() * 1e4), float(t.pvalue)))
rd = r.resample("1D").sum()
for wd in range(7):
    t = ss.ttest_1samp(rd[rd.index.dayofweek == wd], 0.0)
    tests.append(("weekday", wd, float(rd[rd.index.dayofweek == wd].mean() * 1e4), float(t.pvalue)))
order = np.argsort([t[3] for t in tests])
m = len(tests)
survivors = []
for rank, i in enumerate(order):
    if tests[i][3] <= 0.05 / (m - rank):
        survivors.append(tests[i])
    else:
        break
c8 = {"tests": [{"kind": a, "k": b, "mean_bps": c, "p": d} for a, b, c, d in tests], "holm_survivors": survivors, "rules": {}}
for kind, k, mu, _ in survivors:
    sgn = 1.0 if mu > 0 else -1.0
    hh = CD.btc_bars("1h").loc["2019-06-01":]
    # w[t] decided at close of bar t earns open[t+2]/open[t+1]: to be exposed during hour k, set w on the bar two hours earlier
    mask = (hh.index.hour == (k - 2) % 24) if kind == "hour" else ((hh.index + pd.Timedelta(hours=2)).dayofweek == k)
    w = pd.Series(np.where(mask, sgn, 0.0), index=hh.index)
    d = VB.daily(VB.run(hh, w, 7.0, fund_all))["net"]
    c8["rules"][f"{kind}{k}"] = {"validation": summary(d.loc["2020-01-01":"2021-12-31"]), "oos": summary(d.loc["2022-01-01":"2023-12-31"])}
    record(h8, f"calendar_{kind}{k}", {"sign": sgn}, "gen11_C8_val_oos", c8["rules"][f"{kind}{k}"])
passed = [k for k, v in c8["rules"].items() if v["validation"]["sharpe"] > 0.3 and v["oos"]["sharpe"] > 0]
v8 = "REJECT" if not passed else "EXPLORATORY"
F.decide(h8, v8, f"{len(survivors)} Holm survivors of {m}; rules passing VAL+OOS: {passed}", {"protocol": PROTO})
c8["verdict"] = v8
OUT["C8"] = c8

# ------------------------------------------------------------------ C9 funding regime filter for CT1
h9 = H("C9_FUNDING_FILTER_CT1", "crypto/regime", "Skip CT1 longs when funding is extreme.", "Crowded longs are fragile.",
       "filter does not beat unfiltered and random skip", "Bitstamp daily + funding", "single rule", "unfiltered, random skip, halve, cash")
w_ct1 = CS.trend_ensemble(btc_d, {})


def hot_flag(fr: pd.Series, idx: pd.DatetimeIndex) -> pd.Series:
    fr = fr.sort_index()
    hot = (fr > fr.rolling(270, min_periods=135).quantile(0.9).shift(1)).astype(float)
    # bar t (open idx[t]) closes at idx[t]+1D: use the last print at or before that close
    return hot.reindex(idx + pd.Timedelta(days=1), method="ffill").set_axis(idx).fillna(0.0)


def c9_eval(fr, a, b, seed=7):
    hot = hot_flag(fr, btc_d.index)
    long_hot = (w_ct1 > 0) & (hot > 0)
    variants = {"unfiltered": w_ct1, "filtered": w_ct1.where(~long_hot, 0.0), "halve": w_ct1.where(~long_hot, w_ct1 / 2),
                "cash": w_ct1 * 0}
    res = {k: VB.stats(VB.daily(VB.run(btc_d, v, 7.0, fund_all))["net"].loc[a:b])["sharpe"] for k, v in variants.items()}
    elig = np.where((w_ct1 > 0).loc[a:b])[0] + btc_d.index.get_loc(btc_d.loc[a:].index[0])
    n_skip = int(long_hot.loc[a:b].sum())
    rng = np.random.default_rng(seed)
    rnd = []
    for _ in range(300):
        ww = w_ct1.copy()
        if n_skip and len(elig):
            ww.iloc[rng.choice(elig, size=min(n_skip, len(elig)), replace=False)] = 0.0
        rnd.append(VB.stats(VB.daily(VB.run(btc_d, ww, 7.0, fund_all))["net"].loc[a:b])["sharpe"])
    res.update({"skip_days": n_skip, "random_skip_p95": float(np.percentile(rnd, 95)), "random_skip_median": float(np.median(rnd)),
                "filtered_pctile_vs_random": float(np.mean(np.array(rnd) < res["filtered"]))})
    return res


f_btc_rec = rec[rec.venue_symbol == "BTCUSDT"].drop_duplicates("ts").set_index("ts")["rate_raw"].astype(float)
c9 = {"dev_2020_07_2023": c9_eval(f_btc_old, "2020-07-01", "2023-12-31")}
c9["dev_pass"] = bool(c9["dev_2020_07_2023"]["filtered"] > c9["dev_2020_07_2023"]["unfiltered"]
                      and c9["dev_2020_07_2023"]["filtered"] > c9["dev_2020_07_2023"]["random_skip_p95"])
if c9["dev_pass"]:
    c9["confirm_2025_26"] = c9_eval(f_btc_rec, "2025-11-20", "2026-09-20")
    c9["confirm_pass"] = bool(c9["confirm_2025_26"]["filtered"] > c9["confirm_2025_26"]["unfiltered"])
record(h9, "ct1_funding_filter", {}, "gen11_C9", c9)
v9 = "REJECT" if not c9["dev_pass"] else ("EXPLORATORY" if not c9.get("confirm_pass") else "VALIDATION_CANDIDATE")
F.decide(h9, v9, json.dumps({k: v for k, v in c9.items() if k.endswith("pass")}), {"protocol": PROTO})
c9["verdict"] = v9
OUT["C9"] = c9

# ------------------------------------------------------------------ C10 cross-sectional alt momentum (exploratory ceiling)
h10 = H("C10_XS_ALT_MOMENTUM", "crypto/cross-sectional", "30d winners beat losers over the next week among 12 coins.",
        "Attention/flow momentum (Liu, Tsyvinski & Wu 2022 'Common Risk Factors in Cryptocurrency').", "see protocol",
        "mirror daily 2018-2023 (survivorship biased)", "single rule", "equal-weight long all")
closes = {}
for p in sorted((ROOT / "data/raw/dukascopy/crypto").glob("*/*_D1.csv")):
    if p.parent.name in ("ethusd", "btcusd"):
        continue
    d = pd.read_csv(p, sep="\t")
    d.columns = [c.lower() for c in d.columns]
    closes[p.stem.replace("_D1", "")] = d.set_index(pd.to_datetime(d["time"], utc=True))["close"].astype(float)
C = pd.DataFrame(closes).sort_index().loc["2018-01-01":"2023-09-10"]
mom = np.log(C).diff(30)
rets = C.pct_change().shift(-1)                                # return from close t to close t+1 earned by weight set at close t
weights = pd.DataFrame(0.0, index=C.index, columns=C.columns)
for t in range(0, len(C), 7):
    row = mom.iloc[t].dropna()
    if len(row) < 6:
        continue
    wv = pd.Series(0.0, index=C.columns)
    wv[row.nlargest(3).index] = 1 / 6
    wv[row.nsmallest(3).index] = -1 / 6
    weights.iloc[t:t + 7] = wv.to_numpy()
turn = weights.diff().abs().sum(axis=1).fillna(0)
port = (weights * rets.fillna(0)).sum(axis=1) - turn * 15e-4
c10 = {"n_coins": int(C.shape[1]), "train": summary(port.loc["2018-07-01":"2020-12-31"]), "oos": summary(port.loc["2021-01-01":"2023-09-09"])}
c10["pass"] = bool(c10["train"]["sharpe"] >= 0.5 and c10["oos"]["sharpe"] > 0)
record(h10, "xs_mom", {"lb": 30, "rebalance": 7, "n": 3}, "gen11_C10", c10)
v10 = "EXPLORATORY" if c10["pass"] else "REJECT"
F.decide(h10, v10, f"TRAIN {c10['train']['sharpe']:.2f}, OOS {c10['oos']['sharpe']:.2f} (survivorship-biased universe; ceiling EXPLORATORY)", {"protocol": PROTO})
c10["verdict"] = v10
OUT["C10"] = c10

(ROOT / "results" / "v4_gen11.json").write_text(json.dumps(OUT, indent=1, default=float))
for k, v in OUT.items():
    print(k, v.get("verdict"))
print(json.dumps({"C6": {k: OUT["C6"][k] for k in OUT["C6"] if k != "train"}, "C6_train": {k: round(v["sharpe"], 2) for k, v in OUT["C6"]["train"].items()},
                  "C7": OUT["C7"], "C8_survivors": OUT["C8"]["holm_survivors"], "C8_rules": OUT["C8"]["rules"], "C9": OUT["C9"],
                  "C10": {k: OUT["C10"][k] for k in ("train", "oos")}}, indent=1, default=float)[:9000])
