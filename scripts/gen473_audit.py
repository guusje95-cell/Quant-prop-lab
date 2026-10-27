"""Gen473 (descriptive audit of v9.8): (A) how the planning ("expected live") Sharpe is computed and how sensitive it is;
(D) every sleeve alone and in the book: Sharpe by period / year, correlations, leave-one-out marginal contribution, risk share,
drawdowns, and regimes (BTC trend, BTC volatility, altcoin vs BTC). Input: the v98 paper code's own research-pack dump
(results/v98_paper_sleeves.parquet, unit sleeve P&L + 'port'). Writes results/gen473.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm, skew, kurtosis
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
from qpl.lab import binance_pack as B
END = "2026-09-30"; E = np.e; G = 0.5772156649
X = pd.read_parquet(ROOT / "results/v98_paper_sleeves.parquet"); H = X.drop(columns="port").loc[:END + " 23:00"]
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]) if not isinstance(h.index, pd.DatetimeIndex) or h.index.inferred_freq != "D" else h.loc[a:z]
    return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
book = unit(CS.portfolio_v5(H)[0]); bd = dd(book.loc["2022":END]); out = {}
# ---- (A) planning Sharpe ------------------------------------------------------------------------------------------------
T = len(bd); sr = bd.mean() / bd.std(); g3 = float(skew(bd)); g4 = float(kurtosis(bd, fisher=False))
sr_se = np.sqrt((1 - g3 * sr + (g4 - 1) / 4 * sr ** 2) / (T - 1))                 # Mertens / Bailey-LdP standard error (daily units)
A = {"days": T, "Sharpe (annual)": round(float(sr * np.sqrt(365)), 3), "skew": round(g3, 2), "kurtosis": round(g4, 1),
     "standard error of the annual Sharpe (non-normal)": round(float(sr_se * np.sqrt(365)), 3), "by N": {}}
for N in (10, 50, 100, 300, 1000, 1800, 3000):
    sr0 = np.sqrt(1.0 / T) * ((1 - G) * norm.ppf(1 - 1 / N) + G * norm.ppf(1 - 1 / (N * E)))       # project method (null var 1/T)
    sr0b = sr_se * ((1 - G) * norm.ppf(1 - 1 / N) + G * norm.ppf(1 - 1 / (N * E)))                 # same with the non-normal se
    dsr = norm.cdf((sr - sr0) / sr_se)
    A["by N"][str(N)] = {"expected best-of-N luck (annual)": round(float(sr0 * np.sqrt(365)), 3), "planning = Sharpe - luck": round(float((sr - sr0) * np.sqrt(365)), 3),
                         "planning with the non-normal se": round(float((sr - sr0b) * np.sqrt(365)), 3), "DSR (prob. true Sharpe > 0 after selection)": round(float(dsr), 4)}
A["note"] = "planning Sharpe = backtest Sharpe minus the expected maximum Sharpe of N independent zero-edge trials (Bailey & Lopez de Prado). N = 1,800 counts every trial of the project as independent: conservative when trials are correlated variants."
out["A planning"] = A
# ---- (D) sleeves -----------------------------------------------------------------------------------------------------
D = dd(H.loc["2022":END]); ph, W, mult = CS.portfolio_v5(H); Wd = W.reindex(D.index).ffill()
contrib = D * Wd                                                                  # weighted daily sleeve P&L before the book multiplier
yrs = ["2022", "2023", "2024", "2025", "2026"]
S = {}
for c in H.columns:
    x = D[c]; eq = x.cumsum(); dds = float((eq - eq.cummax()).min() / (x.std() * np.sqrt(365)))
    S[c] = {"alone 2022 / 23-24 / 25-26": per(H[c]), "alone 2022-26": shp(H[c]), "by year": [shp(H[c], y, y) for y in yrs],
            "active days share": round(float((x != 0).mean()), 2), "max drawdown in years of its own vol": round(dds, 2),
            "risk share in the book (var contribution)": None, "P&L share of the book": round(float(contrib[c].sum() / contrib.sum().sum()), 3)}
cov = contrib.cov(); tot = contrib.sum(axis=1).var()
for c in H.columns:
    S[c]["risk share in the book (var contribution)"] = round(float(cov[c].sum() / tot), 3)
ref = [shp(book), per(book)]
for c in H.columns:                                                               # leave one out
    b = unit(CS.portfolio_v5(H.drop(columns=c))[0]); S[c]["book without it"] = [shp(b), per(b)]
    S[c]["marginal (book - book without)"] = round(ref[0] - shp(b), 3)
out["D book"] = {"v9.8 paper code": ref, "by year": [shp(book, y, y) for y in yrs], "max drawdown (unit 15% vol)": round(float((dd(book).cumsum() - dd(book).cumsum().cummax()).min()), 3)}
out["D sleeves"] = S
out["D correlation (daily, 2022-26)"] = D.corr().round(2).to_dict()
# regimes from BTC (known at the start of each day)
btc = B.k5("BTC").close.resample("1D").last(); alt = pd.concat([B.k5(c).close.resample("1D").last().rename(c) for c in B.coins() if c not in ("BTC", "ETH")], axis=1)
up = (btc > btc.rolling(200).mean()).shift(1); vol = btc.pct_change().rolling(30).std().shift(1); hv = vol > vol.rolling(365, min_periods=180).median()
altr = (alt.pct_change().mean(axis=1) - btc.pct_change()).rolling(30).sum().shift(1) > 0
R = {}
for nm, m in {"BTC above 200d MA": up, "BTC below 200d MA": ~up.astype(bool), "BTC vol high": hv, "BTC vol low": ~hv.astype(bool), "alts beat BTC (30d)": altr, "BTC beats alts (30d)": ~altr.astype(bool)}.items():
    m = m.reindex(D.index).fillna(False).astype(bool); R[nm] = {"days": int(m.sum()), "book": round(float(bd[m].mean() / bd[m].std() * np.sqrt(365)), 2)}
    for c in H.columns:
        x = D[c][m]; R[nm][c] = round(float(x.mean() / x.std() * np.sqrt(365)), 2) if x.std() > 0 else None
out["D regimes (annualised Sharpe on those days)"] = R
(ROOT / "results/gen473.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1)[:6000])
