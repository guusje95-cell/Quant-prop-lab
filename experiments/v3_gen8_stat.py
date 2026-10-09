"""v3 generation 8: statistical families.
  V5 weekday effects (descriptive scan + Holm correction, TRAIN only)
  V6 ES->NQ / NQ->ES 15-minute lead-lag with a one-bar execution delay
  V7 walk-forward ML (L2 logistic + shallow gradient boosting) on hourly NQ decision points
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.research import factory as F, pipeline as P  # noqa: E402
from qpl.statistics import tests as T  # noqa: E402
from qpl.strategies import v3_intraday as V  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TRAIN, VAL, OOS = P.SPLITS["train"], P.SPLITS["validation"], P.SPLITS["oos"]
out = {}

# ------------------------------------------------------------------ V5 weekday
h5 = F.Hypothesis("V5_WEEKDAY", "calendar/weekday", "Mean RTH open-to-close return differs by weekday in US index futures.",
                  "Weekly flow patterns (weekend risk, Monday effect literature).", "No weekday significant after Holm correction on TRAIN.",
                  "15m bars", "5 weekdays x 3 markets = 15 tests", "zero mean", "Holm-adjusted p < 0.05 AND same sign in VALIDATION")
h5.register()
rows = []
for fut, proxy in (("ES", "US500"), ("NQ", "US100"), ("YM", "US30")):
    ctx = P.context("dukascopy", proxy, "M15")
    t = V.daily_rth_table(ctx)
    t = t[(t.first_min == 570) & (t.last_min == 945)]
    r = np.log(t["close"] / t["open"]) * 1e4
    r.index = pd.DatetimeIndex(r.index)
    for dw in range(5):
        x = r.loc[TRAIN[0]:TRAIN[1]]; x = x[x.index.dayofweek == dw]
        y = r.loc[VAL[0]:VAL[1]]; y = y[y.index.dayofweek == dw]
        tstat, p = st.ttest_1samp(x, 0)
        rows.append(dict(mkt=fut, dow=dw, train_mean_bp=x.mean(), t=tstat, p=p, val_mean_bp=y.mean()))
wd = pd.DataFrame(rows).sort_values("p")
m = len(wd)
wd["holm_p"] = np.minimum(1, np.maximum.accumulate((m - np.arange(m)) * wd["p"].to_numpy()))
out["V5_weekday"] = wd.round(4).to_dict("records")
sig = wd[wd.holm_p < 0.05]
F.append({"kind": "experiment", "hypothesis_id": "V5_WEEKDAY", "summary": {"n_tests": m, "n_significant_holm": int(len(sig))}})
F.decide(h5, "REJECT" if sig.empty else "EXPLORATORY", f"{len(sig)} of {m} weekday tests significant after Holm (min holm p {wd.holm_p.min():.3f})")

# ------------------------------------------------------------------ V6 lead-lag
h6 = F.Hypothesis("V6_LEADLAG", "cross-market/lead-lag", "The 15-minute return of one index future predicts the next 15-minute return of the other after a one-bar delay.",
                  "Information diffusion across related contracts (Hou 2007, lead-lag literature); index arbitrage keeps it short-lived.",
                  "Slope t-stat < 2 on TRAIN or net trading rule Sharpe < 0.5.", "Synchronized 15m bars US500/US100", "k {1,2} sigma divergence",
                  "zero", "config/promotion_criteria.json")
h6.register()
a = P.context("dukascopy", "US500", "M15"); b = P.context("dukascopy", "US100", "M15")
idx = a.index.intersection(b.index)
a, b = a.loc[idx], b.loc[idx]
rth = (a["rth"] & a["valid_day"] & b["rth"]).to_numpy()
ra = np.log(a.close / a.open).to_numpy(); rbq = np.log(b.close / b.open).to_numpy()
same_day = np.r_[a["date"].to_numpy()[1:] == a["date"].to_numpy()[:-1], False]
nxt_ok = rth & np.r_[rth[1:], False] & same_day
X = pd.DataFrame({"es": ra, "nq": rbq, "es_next": np.r_[ra[1:], np.nan], "nq_next": np.r_[rbq[1:], np.nan]}, index=idx)[nxt_ok]
ll = {}
for per, (s0, s1) in {"train": TRAIN, "validation": VAL}.items():
    x = X.loc[s0:s1]
    for tgt, own, oth in (("nq_next", "nq", "es"), ("es_next", "es", "nq")):
        import statsmodels.api as sm
        mdl = sm.OLS(x[tgt], sm.add_constant(x[[own, oth]])).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
        ll[f"{per}:{tgt}"] = {"coef_own": float(mdl.params[own]), "t_own": float(mdl.tvalues[own]),
                              "coef_other": float(mdl.params[oth]), "t_other": float(mdl.tvalues[oth]), "r2": float(mdl.rsquared)}
# trading rule: NQ next bar in direction of ES-minus-NQ divergence; cost = NQ round trip (normalized)
cost_ret = (2 * 0.25 + 2.80 / 20) / 19900
for k in (1.0, 2.0):
    for per, (s0, s1) in {"train": TRAIN, "validation": VAL}.items():
        x = X.loc[s0:s1]
        dv = x.es - x.nq
        s = dv.rolling(500, min_periods=200).std().shift(1)
        pos = np.sign(dv).where(dv.abs() > k * s, 0)
        pnl = (pos * x.nq_next - pos.abs() * cost_ret) * 19900 * 20
        d = pnl.groupby(pnl.index.tz_convert("America/New_York").normalize()).sum()
        ll[f"rule_k{k}:{per}"] = {"trades": int((pos != 0).sum()), "sharpe": float(d.mean() / d.std() * np.sqrt(252)),
                                  "gross_sharpe": float(((pos * x.nq_next) * 19900 * 20).groupby(pnl.index.tz_convert("America/New_York").normalize()).sum().pipe(lambda z: z.mean() / z.std() * np.sqrt(252)))}
out["V6_leadlag"] = ll
best = max(v["sharpe"] for k_, v in ll.items() if k_.startswith("rule") and k_.endswith("train"))
F.append({"kind": "experiment", "hypothesis_id": "V6_LEADLAG", "summary": ll})
F.decide(h6, "REJECT" if best < 0.5 else "EXPLORATORY", f"best TRAIN net Sharpe of divergence rule {best:.2f}; regression t-stats {[round(v['t_other'],2) for k_, v in ll.items() if not k_.startswith('rule')]}")

# ------------------------------------------------------------------ V7 ML
h7 = F.Hypothesis("V7_ML_INTRADAY", "adaptive/statistical model",
                  "A regularized model of interpretable intraday state (noise-normalized move, gap, trend efficiency, vol ratio, relative strength, time) predicts the sign of the rest-of-session return better than simple momentum.",
                  "Combines momentum/reversal/regime information; tests whether conditioning adds value over H3.",
                  "Walk-forward net Sharpe below the pure-momentum baseline (sign of noise-normalized move) or < 0.5.",
                  "15m US100 + US500 bars", "logistic C {0.1}, GBM depth 2/200 trees; threshold {0.03,0.06}; expanding yearly walk-forward with whole-day embargo",
                  "sign(move from open / noise sigma) at the same decision points", "config/promotion_criteria.json")
h7.register()
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

c = P.context("dukascopy", "US100", "M15"); e = P.context("dukascopy", "US500", "M15")
sig, _ = V._tod_sigma(c, 14)
tw = V._twap(c)
C, O = c.close.to_numpy(), c.open.to_numpy()
op, pc, atr = c.rth_open.to_numpy(), c.prev_rth_close.to_numpy(), c.atr_d.to_numpy()
et = c.et_min.to_numpy(); date = c["date"].to_numpy()
rthv = (c.rth & c.valid_day).to_numpy()
ecl = e.close.reindex(c.index).to_numpy(); eop = e.rth_open.reindex(c.index).to_numpy()
t = V.daily_rth_table(c)
eff = (t.close.diff(10).abs() / t.close.diff().abs().rolling(10).sum())
rv_ratio = t.close.pct_change().rolling(5).std() / t.close.pct_change().rolling(20).std()
pret = t.close.pct_change()
from qpl.features.intraday import asof_prior
f_eff, f_rvr, f_pret = (asof_prior(s, date) for s in (eff, rv_ratio, pret))
# close at 16:00 per date (label) and next-open
close16 = pd.Series(C[(et == 945) & rthv], index=date[(et == 945) & rthv])
close16 = close16[~close16.index.duplicated()]
c16 = pd.Series(date).map(close16).to_numpy()
nxt_open = np.r_[O[1:], np.nan]
dec = rthv & ((et + 15) % 60 == 0) & (et + 15 >= 600) & (et + 15 <= 900)
D = pd.DataFrame({
    "date": date, "slot": (et + 15) // 60,
    "z_move": (C / op - 1) / sig, "gap": (op - pc) / atr, "pret": f_pret * 100, "eff": f_eff, "rvr": f_rvr,
    "rel": np.log(C / op) - np.log(ecl / eop), "twap_dev": (C - tw) / (op * sig), "dow": c.dow.to_numpy(),
    "y_ret": (c16 - nxt_open) / nxt_open, "entry": nxt_open}, index=c.index)[dec].dropna()
feats = ["z_move", "gap", "pret", "eff", "rvr", "rel", "twap_dev", "slot", "dow"]
D["year"] = pd.DatetimeIndex(D["date"]).year
cost_r = (2 * 0.25 + 2.80 / 20) / 19900
res = {}
for mname, mk in {"logit": lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=500)),
                  "gbm": lambda: HistGradientBoostingClassifier(max_depth=2, max_iter=200, learning_rate=0.05)}.items():
    preds = []
    for Y in range(2016, 2024):
        tr_ = D[D.year < Y]
        te = D[D.year == Y]
        if len(te) == 0:
            continue
        m_ = mk().fit(tr_[feats], (tr_.y_ret > 0).astype(int))
        p = m_.predict_proba(te[feats])[:, 1]
        preds.append(pd.Series(p, index=te.index))
    pr = pd.concat(preds)
    for thr in (0.03, 0.06):
        Dt = D.loc[pr.index].copy(); Dt["p"] = pr
        Dt["pos"] = np.where(Dt.p > 0.5 + thr, 1, np.where(Dt.p < 0.5 - thr, -1, 0))
        first = Dt[Dt.pos != 0].groupby("date").head(1)            # one trade per day: first qualifying check
        pnl = (first.pos * first.y_ret - cost_r) * 19900 * 20
        days_ = pd.DatetimeIndex(sorted(D.loc[pr.index, "date"].unique()))
        d = pnl.groupby(pd.DatetimeIndex(first["date"])).sum().reindex(days_, fill_value=0)
        for per, (s0, s1) in {"wf_2016_2020": ("2016-01-01", "2020-12-31"), "wf_2021_2023": OOS}.items():
            x = d.loc[s0:s1]
            res[f"{mname}_thr{thr}:{per}"] = {"sharpe": float(x.mean() / x.std() * np.sqrt(252)), "trades": int((x != 0).sum()),
                                              "total": float(x.sum()), "auc_proxy_hit": float(((first.pos * first.y_ret) > 0).mean())}
# baseline: pure momentum sign of z_move with |z| > 1.25 (H3-like), first check per day, hold to close
Bq = D[D.z_move.abs() > 1.25].groupby("date").head(1)
pnl = (np.sign(Bq.z_move) * Bq.y_ret - cost_r) * 19900 * 20
days_ = pd.DatetimeIndex(sorted(D["date"].unique()))
d = pnl.groupby(pd.DatetimeIndex(Bq["date"])).sum().reindex(days_, fill_value=0)
for per, (s0, s1) in {"wf_2016_2020": ("2016-01-01", "2020-12-31"), "wf_2021_2023": OOS}.items():
    x = d.loc[s0:s1]
    res[f"baseline_momentum:{per}"] = {"sharpe": float(x.mean() / x.std() * np.sqrt(252)), "trades": int((x != 0).sum()), "total": float(x.sum())}
out["V7_ml"] = res
F.append({"kind": "experiment", "hypothesis_id": "V7_ML_INTRADAY", "summary": res,
          "note": "walk-forward 2016-2020 used for the decision; 2021-2023 reported (semi-independent: H3 family already evaluated there)"})
best_ml = max(v["sharpe"] for k_, v in res.items() if not k_.startswith("baseline") and k_.endswith("2016_2020"))
base = res["baseline_momentum:wf_2016_2020"]["sharpe"]
F.decide(h7, "REJECT" if (best_ml < 0.5 or best_ml <= base) else "EXPLORATORY",
         f"best ML walk-forward 2016-20 Sharpe {best_ml:.2f} vs momentum baseline {base:.2f}")
(ROOT / "results" / "v3_gen8_stat.json").write_text(json.dumps(out, indent=1, default=float))
print(json.dumps({k: v for k, v in out.items() if k != "V5_weekday"}, indent=1, default=float))
print(pd.DataFrame(out["V5_weekday"]).head(6).to_string())
