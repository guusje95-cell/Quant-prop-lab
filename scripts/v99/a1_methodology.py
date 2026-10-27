"""v9.9 A1 (methodology audit of the 'planning' / estimated-live Sharpe of v9.8). Writes results/v99/a1_methodology.json.
  1. reproduce: SR - E[max SR of N zero-edge trials] (project method)
  2. uncertainty of the observed Sharpe: non-normal (Mertens) SE, autocorrelation-adjusted (Lo 2002) annualisation, stationary block bootstrap CI
  3. DSR (Bailey & Lopez de Prado 2014) for N in a range
  4. Harvey-Liu (2015) multiple-testing haircut (Bonferroni, Holm best-trial, BHY) for N in a range
  5. PBO by CSCV (Bailey et al. 2017) on a selection family we can rebuild exactly: the 502 equal-risk books made of every subset (>= 2) of
     the 9 v9.8 sleeves; also the empirical out-of-sample decay of the in-sample winner and the effective number of independent books
     in that family (eigenvalue entropy)
  6. time decay: Sharpe by period."""
import itertools
import json
import sys
from math import comb
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm, skew, kurtosis
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
END = "2026-09-30"; G = 0.5772156649; rng = np.random.default_rng(7)
H = pd.read_parquet(ROOT / "results/v98_paper_sleeves.parquet").drop(columns="port").loc[:END + " 23:00"]
dd = lambda h: h.groupby(h.index.floor("D")).sum()
book = dd(CS.portfolio_v5(H)[0].loc["2022":END]); r = book.to_numpy(); T = len(r); yrs = T / 365
sr_d = r.mean() / r.std(ddof=1); SR = sr_d * np.sqrt(365)
emax = lambda N: (1 - G) * norm.ppf(1 - 1 / N) + G * norm.ppf(1 - 1 / (N * np.e))
out = {"data": {"days": T, "from": str(book.index[0].date()), "to": str(book.index[-1].date()), "observed Sharpe": round(SR, 3)}}
NS = [100, 300, 1000, 1849, 3000]
# 1 reproduce
out["1 project method (SR - expected max of N null trials, null variance 1/T)"] = {str(N): round(SR - emax(N) / np.sqrt(T) * np.sqrt(365), 3) for N in NS}
# 2 uncertainty
g3, g4 = skew(r), kurtosis(r, fisher=False)
se_nn = np.sqrt((1 - g3 * sr_d + (g4 - 1) / 4 * sr_d ** 2) / (T - 1)) * np.sqrt(365)
rho = [pd.Series(r).autocorr(k) for k in range(1, 11)]
q = 365; eta = q / np.sqrt(q + 2 * sum((q - k) * pd.Series(r).autocorr(k) for k in range(1, 31)))     # Lo (2002) annualisation for daily data, 30 lags
SR_lo = sr_d * eta
def block_boot(x, B=2000, L=20):
    n = len(x); out = []
    for _ in range(B):
        idx = []
        while len(idx) < n:
            s = rng.integers(0, n); l = rng.geometric(1 / L); idx += [(s + i) % n for i in range(l)]
        y = x[np.array(idx[:n])]; out.append(y.mean() / y.std(ddof=1) * np.sqrt(365))
    return np.array(out)
bs = block_boot(r)
out["2 uncertainty of the observed Sharpe"] = {"skew": round(float(g3), 2), "kurtosis": round(float(g4), 1), "SE (non-normal)": round(float(se_nn), 3),
    "95% CI (non-normal SE)": [round(float(SR - 1.96 * se_nn), 2), round(float(SR + 1.96 * se_nn), 2)],
    "autocorrelation lags 1-5": [round(float(x), 3) for x in rho[:5]], "Lo-adjusted annual Sharpe": round(float(SR_lo), 3),
    "stationary block bootstrap (mean block 20 d) 5% / 50% / 95%": [round(float(np.percentile(bs, p)), 2) for p in (5, 50, 95)]}
# 3 DSR
out["3 DSR = P(true SR > E[max of N nulls])"] = {str(N): round(float(norm.cdf((sr_d - emax(N) / np.sqrt(T)) * np.sqrt(T - 1) / np.sqrt(1 - g3 * sr_d + (g4 - 1) / 4 * sr_d ** 2))), 6) for N in NS}
# 4 Harvey-Liu haircut
t = SR * np.sqrt(yrs); p = 2 * norm.sf(t); HL = {}
for N in NS:
    c = sum(1 / i for i in range(1, N + 1))
    for nm, padj in (("Bonferroni", min(1, N * p)), ("BHY (best trial)", min(1, N * c * p))):
        tadj = norm.isf(padj / 2) if padj < 1 else 0.0
        HL.setdefault(nm, {})[str(N)] = round(float(tadj / np.sqrt(yrs)), 3)
out["4 Harvey-Liu haircut Sharpe (t-stat of the observed Sharpe = %.2f)" % t] = HL
# 5 PBO / CSCV on the sleeve-subset family
cols = list(H.columns); fam = {}
for k in range(2, len(cols) + 1):
    for sub in itertools.combinations(cols, k):
        fam[" + ".join(sub)] = dd(CS.portfolio_v5(H[list(sub)])[0].loc["2022":END]).reindex(book.index).fillna(0.0)
M = pd.DataFrame(fam).to_numpy(); nb = M.shape[1]
S = 16; blocks = np.array_split(np.arange(T), S); combos = list(itertools.combinations(range(S), S // 2))
pick = [combos[i] for i in rng.choice(len(combos), size=min(2000, len(combos)), replace=False)]
logits, is_best, oos_best, oos_med = [], [], [], []
srf = lambda X: X.mean(0) / X.std(0, ddof=1) * np.sqrt(365)
for c in pick:
    tr = np.concatenate([blocks[i] for i in c]); te = np.concatenate([blocks[i] for i in range(S) if i not in c])
    a = srf(M[tr]); b = srf(M[te]); j = int(np.argmax(a)); rk = (b < b[j]).sum() + 0.5 * ((b == b[j]).sum() - 1)
    w = (rk + 1) / (nb + 1); logits.append(np.log(w / (1 - w))); is_best.append(a[j]); oos_best.append(b[j]); oos_med.append(np.median(b))
ev = np.linalg.eigvalsh(np.corrcoef(M.T)); ev = ev[ev > 1e-12] / ev[ev > 1e-12].sum(); neff = float(np.exp(-(ev * np.log(ev)).sum()))
v98_rank = None
full = srf(M); v98_rank = int((full > full[list(fam).index(" + ".join(cols))]).sum()) + 1
out["5 PBO on the 502 sleeve-subset books (CSCV, 16 blocks, 2000 splits)"] = {"PBO (share of splits where the in-sample winner is below the out-of-sample median)": round(float(np.mean(np.array(logits) <= 0)), 3),
    "in-sample winner: mean IS Sharpe / mean OOS Sharpe": [round(float(np.mean(is_best)), 2), round(float(np.mean(oos_best)), 2)],
    "OOS median of all books": round(float(np.mean(oos_med)), 2), "selection decay of the winner (IS - OOS)": round(float(np.mean(is_best) - np.mean(oos_best)), 2),
    "effective number of independent books (eigenvalue entropy)": round(neff, 1), "rank of the full v9.8 book among the 502 (full sample)": v98_rank,
    "best full-sample subset": [list(fam)[int(np.argmax(full))], round(float(full.max()), 3)]}
# 6 time decay
yr = {y: round(float(book.loc[y].mean() / book.loc[y].std() * np.sqrt(365)), 2) for y in ("2022", "2023", "2024", "2025", "2026")}
out["6 Sharpe by year"] = yr
(ROOT / "results/v99/a1_methodology.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
