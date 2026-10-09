"""V6 gen15 a-c: regime / change-point / factor-momentum overlays on the TREND and CARRY futures sleeves.
Protocol config/v6_gen15_protocol.json (committed d8b1625 before this ran)."""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
from scipy import stats as ss

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import panel as PB  # noqa: E402
from qpl.data import futures_panel as FP  # noqa: E402
from qpl.research import factory as F, v6  # noqa: E402
from qpl.strategies import futures_factors as FF  # noqa: E402

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
PROTO = "config/v6_gen15_protocol.json"
P = FP.build(); U, utab = FP.universe(P)
ret, cost, cy = P["ret"][U], P["cost"][U], P["carry"][U]
SIG = PB.sigma(ret)
trend_sig = ((FF.ct1_transfer(ret).fillna(0) + FF.tsmom(ret).fillna(0) + FF.ewmac(ret).fillna(0)) / 3).where(ret.notna().cumsum() > 0)
T = PB.run(ret, trend_sig, cost, sig=SIG)["net"]
C = PB.run(ret, FF.carry(ret, cy, 21), cost, sig=SIG)["net"]
M = PB.run(ret, FF.long_rp(ret), cost, sig=SIG)["net"]
S = pd.DataFrame({"T": T, "C": C}).loc["1980-01-01":]
B0 = S.mean(axis=1)
OOS = ("1995-01-01", "2013-12-31"); SEC = ("2014-01-01", "2024-03-28")
YEARS = range(1995, 2025)


def sharpe(x):
    x = x.dropna()
    return float(x.mean() / x.std() * np.sqrt(256)) if len(x) > 20 and x.std() > 0 else 0.0


def apply(wT: pd.Series) -> pd.Series:
    """wT = weight on TREND decided through day t (CARRY gets 1-wT); applied to P&L from t+1; scaled so that equal weight = B0."""
    w = wT.reindex(S.index).ffill().shift(1)
    return w * S["T"] + (1 - w) * S["C"]


# ---------------- features for the HMM (weekly, Friday)
mv = M.loc["1980":].rolling(20).std() * np.sqrt(256)
X = pd.DataFrame({"r": M.loc["1980":], "lv": np.log(mv)}).resample("W-FRI").agg({"r": "sum", "lv": "last"}).dropna()


def forward_filter(model: GaussianHMM, Xa: np.ndarray) -> np.ndarray:
    K = model.n_components
    ll = np.column_stack([ss.multivariate_normal(model.means_[k], model.covars_[k], allow_singular=True).logpdf(Xa) for k in range(K)])
    a = np.log(model.startprob_ + 1e-300) + ll[0]
    out = np.zeros_like(ll)
    logA = np.log(model.transmat_ + 1e-300)
    for t in range(len(Xa)):
        if t > 0:
            a = np.logaddexp.reduce(a[:, None] + logA, axis=0) + ll[t]
        a = a - np.logaddexp.reduce(a)
        out[t] = np.exp(a)
    return out


hmm_w = pd.Series(np.nan, index=S.index)
hmm_info = {}
for Y in YEARS:
    tr = X.loc[: f"{Y - 1}-12-31"]
    mdl = GaussianHMM(n_components=2, covariance_type="full", n_iter=200, random_state=0).fit(tr.to_numpy())
    stress = int(np.argmax(mdl.means_[:, 1]))                     # state with higher vol = "stress"
    pr = forward_filter(mdl, X.loc[: f"{Y}-12-31"].to_numpy())
    st = pd.Series(np.where(pr[:, stress] > 0.5, 1, 0), index=X.loc[: f"{Y}-12-31"].index)  # 1 = stress
    st_d = st.reindex(S.index, method="ffill")                   # weekly state known at Friday close -> following days
    trn = S.loc[: f"{Y - 1}-12-31"].join(st_d.rename("st")).dropna()
    sh = {(k, s): sharpe(trn.loc[trn.st == s, k]) for k in ("T", "C") for s in (0, 1)}
    wy = {}
    for s in (0, 1):
        a, b = max(sh[("T", s)], 0), max(sh[("C", s)], 0)
        wy[s] = 0.5 if a + b == 0 else a / (a + b)
    days = S.loc[f"{Y}-01-01":f"{Y}-12-31"].index
    hmm_w.loc[days] = st_d.loc[days].map(wy).to_numpy()
    hmm_info[Y] = {"w_calm": round(wy[0], 2), "w_stress": round(wy[1], 2), "share_stress": round(float(st_d.loc[days].mean()), 2)}

# ---------------- BOCPD on B0 (online by construction)
def bocpd(x: np.ndarray, hazard=1 / 250, mu0=0.0, kappa0=1.0, alpha0=1.0, beta0=1e-4, rmax=600):
    T_ = len(x); p_short = np.zeros(T_)
    R = np.array([1.0]); mu = np.array([mu0]); ka = np.array([kappa0]); al = np.array([alpha0]); be = np.array([beta0])
    for t in range(T_):
        scale = np.sqrt(be * (ka + 1) / (al * ka))
        pred = ss.t.pdf(x[t], 2 * al, loc=mu, scale=scale)
        growth = R * pred * (1 - hazard)
        cp = (R * pred * hazard).sum()
        R = np.append(cp, growth); R = R / R.sum()
        mu_n = (ka * mu + x[t]) / (ka + 1); ka_n = ka + 1; al_n = al + 0.5; be_n = be + ka * (x[t] - mu) ** 2 / (2 * (ka + 1))
        mu = np.append(mu0, mu_n); ka = np.append(kappa0, ka_n); al = np.append(alpha0, al_n); be = np.append(beta0, be_n)
        if len(R) > rmax:
            R, mu, ka, al, be = R[:rmax], mu[:rmax], ka[:rmax], al[:rmax], be[:rmax]; R = R / R.sum()
        p_short[t] = R[:21].sum()
    return p_short


x = B0.fillna(0).to_numpy()
beta0 = float(np.var(x[:252]))                                   # 1980 data only (pre-OOS)
pshort = pd.Series(bocpd(x, beta0=beta0), index=B0.index)
boc_scale = pd.Series(np.where(pshort > 0.5, 0.5, 1.0), index=B0.index)
boc_pnl = boc_scale.shift(1) * B0

# ---------------- factor momentum
fm = pd.DataFrame({k: S[k].rolling(252).mean() / S[k].rolling(252).std() for k in ("T", "C")}).clip(lower=0)
fm_w = (fm["T"] / fm.sum(axis=1)).where(fm.sum(axis=1) > 0, 0.5)

# ---------------- evaluate with random controls
rng = np.random.default_rng(15)


def block_shuffle(w: pd.Series, a, z, block=63):
    seg = w.loc[a:z].to_numpy(); n = len(seg)
    blocks = [seg[i:i + block] for i in range(0, n, block)]
    order = rng.permutation(len(blocks))
    return pd.Series(np.concatenate([blocks[i] for i in order])[:n], index=w.loc[a:z].index)


res = {"B0": {"OOS": sharpe(B0.loc[OOS[0]:OOS[1]]), "SEC": sharpe(B0.loc[SEC[0]:SEC[1]])},
       "TREND_only": {"OOS": sharpe(S["T"].loc[OOS[0]:OOS[1]]), "SEC": sharpe(S["T"].loc[SEC[0]:SEC[1]])},
       "CARRY_only": {"OOS": sharpe(S["C"].loc[OOS[0]:OOS[1]]), "SEC": sharpe(S["C"].loc[SEC[0]:SEC[1]])}}
for name, pnl, wser, kind in (("H15a_HMM_REGIME", apply(hmm_w), hmm_w, "w"), ("H15c_FACTOR_MOMENTUM", apply(fm_w), fm_w, "w"),
                              ("H15b_BOCPD_DERISK", boc_pnl, boc_scale, "scale")):
    o = {"OOS": sharpe(pnl.loc[OOS[0]:OOS[1]]), "SEC": sharpe(pnl.loc[SEC[0]:SEC[1]])}
    rnd = []
    for _ in range(200):
        ws = block_shuffle(wser, *OOS)
        if kind == "w":
            p = apply(ws).loc[OOS[0]:OOS[1]]
        else:
            p = (ws.reindex(B0.index).shift(1) * B0).loc[OOS[0]:OOS[1]]
        rnd.append(sharpe(p))
    o["random_p95"] = float(np.percentile(rnd, 95)); o["random_median"] = float(np.median(rnd))
    o["adopt"] = bool(o["OOS"] >= res["B0"]["OOS"] + 0.10 and o["OOS"] > o["random_p95"])
    res[name] = o
    v6.record(name, "futures/regime-overlay", name, {}, "WF_OOS_1995_2013", o, 15, PROTO, "futures sleeves")
    F.decide(F.Hypothesis(name, "futures/regime-overlay", "", "", "", "", "", "", PROTO, generation=15),
             "PROMISING_BUT_UNVALIDATED" if o["adopt"] else "REJECTED",
             f"WF OOS 1995-2013 {o['OOS']:.2f} vs B0 {res['B0']['OOS']:.2f}, random p95 {o['random_p95']:.2f}; contaminated 2014-24 {o['SEC']:.2f}", {"protocol": PROTO})
res["hmm_by_year"] = hmm_info
res["bocpd_share_derisked_oos"] = float((boc_scale.loc[OOS[0]:OOS[1]] < 1).mean())
res["corr_T_C"] = {"OOS": float(S.loc[OOS[0]:OOS[1]].corr().iloc[0, 1]), "SEC": float(S.loc[SEC[0]:SEC[1]].corr().iloc[0, 1])}
pd.DataFrame({"T": S["T"], "C": S["C"], "B0": B0, "LONG_RP": M}).to_parquet(ROOT / "results/v6_sleeves_pnl.parquet")
(ROOT / "results/v6_gen15_regime.json").write_text(json.dumps(res, indent=1, default=float))
print(json.dumps({k: v for k, v in res.items() if k != "hmm_by_year"}, indent=1))
print(pd.DataFrame(hmm_info).T.tail(12))
