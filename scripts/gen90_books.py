"""Gen90 (config/gen90_protocol.json): books with the H4 deleveraging bounce. Writes results/gen90_stats.csv, results/gen90_prop.csv,
results/gen90_v5.csv, results/cache_gen90_hourly.parquet, results/gen90_books.png."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen89_check.py")}
exec(open(ROOT / "scripts/gen89_check.py").read().split("rows = []")[0], g)
inner = g["g"]
CS, B, CFD, d2h, IDX = inner["CS"], g["B"], g["CFD"], g["d2h"], g["IDX"]
import importlib; CS = importlib.reload(CS)                                  # standard v5_weights (no event patch)
sys.path.insert(0, str(ROOT / "src")); from qpl.lab import propfirms as PF
fhp = g["fhp"]
w, _ = g["sig_w"](0.10); pos = d2h(w)
h4_cfd = fhp(pos, 3.3).reindex(IDX).fillna(0.0); h4_sf = fhp(pos, 0.0).reindex(IDX).fillna(0.0)
C85 = pd.read_parquet(ROOT / "results/cache_gen85_hourly.parquet").reindex(IDX).fillna(0.0)
S0 = inner["ns"]["sleeves"](0.0, 1.0).reindex(IDX).fillna(0.0)
BASE = {"C*": C85["B1 swap-aware C* thr 0.5"], "Weiss expiry": C85["ref Weiss BTC/ETH"]}
SF = {k: S0[k] for k in ("C*", "premium carry", "trend 4h", "Weiss expiry")}
pf = lambda cols: CS.portfolio_v5(pd.DataFrame(cols).fillna(0.0))[0]
books = {"NEW CFD book (swap-aware C* + Weiss + deleveraging bounce)": pf({**BASE, "delev bounce": h4_cfd}),
         "Gen85 CFD book (swap-aware C* + Weiss)": pf(BASE),
         "NEW swap-free book (+ deleveraging bounce)": pf({**SF, "delev bounce": h4_sf}), "Gen83 swap-free book": pf(SF)}
pd.DataFrame(books).to_parquet(ROOT / "results/cache_gen90_hourly.parquet")
rows = []
for n, h in books.items():
    d = h.groupby(h.index.floor("D")).sum().loc["2022-01-01":"2026-09-30"]; x = d * 0.15 / (d.std() * np.sqrt(365))
    eq = (1 + x).cumprod(); m = (1 + x).resample("ME").prod() - 1; y = (1 + x).resample("YE").prod() - 1
    sh = lambda a, b: x.loc[a:b].mean() / x.loc[a:b].std() * np.sqrt(365)
    rows.append({"book": n, "Sharpe 2022-26": sh("2022", "2026"), "TEST 23-24": sh("2023", "2024"), "HOLD 25-26": sh("2025", "2026"),
                 "CAGR@15%vol": eq.iloc[-1] ** (365 / len(x)) - 1, "MaxDD": (eq / eq.cummax() - 1).min(), "pos months": (m > 0).mean(),
                 "worst month": m.min(), "worst day": x.min(), **{str(k.year): v for k, v in y.items()}})
S = pd.DataFrame(rows); S.to_csv(ROOT / "results/gen90_stats.csv", index=False); pd.set_option("display.width", 260); print(S.round(3).to_string(), flush=True)


def to_daily_stop(h, stop):
    out = []
    for d, gg in h.groupby(h.index.floor("D")):
        p = np.cumprod(1 + gg.to_numpy())
        if stop > 0 and (p <= 1 - stop).any():
            k = int(np.argmax(p <= 1 - stop)); close = p[k] - 0.001
            out.append((d, close - 1, min(p[:k + 1].min(), close) - 1, max(p[:k + 1].max(), 1.0) - 1))
        else:
            out.append((d, p[-1] - 1, min(p.min(), 1.0) - 1, max(p.max(), 1.0) - 1))
    return pd.DataFrame(out, columns=["day", "net", "worst", "best"]).set_index("day")


P = []
for n in books:
    h = books[n].loc["2022-01-01":"2026-09-30 23:00"]; dd = h.groupby(h.index.floor("D")).sum(); h = h * 0.15 / (dd.std() * np.sqrt(365))
    keys = ("FundedNext Stellar 2-Step $100k swap-free",) if "swap-free" in n else ("FTMO 2-Step $100k", "FundedNext Stellar 2-Step $100k", "BrightFunded Two-Step Classic $100k")
    for key in keys:
        f = PF.PRESETS[key]
        for sc, sf, st in ((1.0, 0.6, 0.5), (1.5, 1.0, 0.6)):
            hc = to_daily_stop(h * sc, st * f.daily_loss); hf = to_daily_stop(h * sf, st * f.daily_loss)
            a = PF.attempts(hc, f, 1.0)
            pb = PF.pipeline(hc, f, 5, 1, 1.0, 1.0, daily_fd=hf, horizon_days=730, method="bootstrap", n_boot=500, block=20, seed=11)
            P.append({"book": n, "firm": f.name, "setting": f"{sc}/{sf}/{st}", "pass": a["P_pass"], "days_to_pass": a["median_days_to_pass"],
                      "mean_net": pb["net_mean"], "p10": pb["net_p10"], "P_profit": pb["P_profit"]})
            print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in P[-1].items()}, flush=True)
pd.DataFrame(P).to_csv(ROOT / "results/gen90_prop.csv", index=False)

# v5 test at perp costs
H1 = B.panel("close", "1h", ["BTC", "ETH"]).loc[:"2026-09-30 23:00"]; r1 = H1.pct_change(fill_method=None).fillna(0.0)
pp = pos[["BTC", "ETH"]].reindex(r1.index).fillna(0.0)
fund = CS._funding_hourly(["BTC", "ETH"], r1.index)
h4p = ((pp * r1).sum(axis=1) - (pp * fund).sum(axis=1) - pp.diff().abs().fillna(pp.abs()).sum(axis=1) * 5 / 1e4)
H5 = CS.v5_sleeves(); V5 = CS.portfolio_v5(H5)[0]; V6 = CS.portfolio_v5(pd.concat([H5, h4p.rename("delev bounce")], axis=1).fillna(0.0))[0]
dsh = g["dsh"]; cst = H5["C*"].groupby(H5.index.floor("D")).sum()
r = {"DEV 2022": dsh(h4p, "2022", "2022-12-31"), "TEST": dsh(h4p, "2023", "2024-12-31"), "HOLD": dsh(h4p, "2025", "2026-09-30"),
     "corr C*": float(pd.concat([cst, h4p.groupby(h4p.index.floor("D")).sum()], axis=1).loc["2022":].corr().iloc[0, 1]),
     "corr cascade": float(pd.concat([H5["cascade limit strict"], h4p], axis=1).fillna(0).pipe(lambda z: z.groupby(z.index.floor("D")).sum()).loc["2022":].corr().iloc[0, 1]),
     "v5": dsh(V5, "2022", "2026-09-30"), "v5 + delev": dsh(V6, "2022", "2026-09-30"), "v5 TEST": dsh(V5, "2023", "2024-12-31"), "v5+ TEST": dsh(V6, "2023", "2024-12-31"),
     "v5 HOLD": dsh(V5, "2025", "2026-09-30"), "v5+ HOLD": dsh(V6, "2025", "2026-09-30")}
r["pass"] = bool(r["DEV 2022"] > 0 and r["TEST"] >= 0.8 and r["HOLD"] >= 0.5 and r["corr C*"] <= 0.3 and r["v5 + delev"] > r["v5"])
print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
pd.DataFrame([r]).to_csv(ROOT / "results/gen90_v5.csv", index=False)
print("done", flush=True)
