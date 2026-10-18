"""Gen96 parts B-D: execution delays and a deliberate look-ahead control, risk (bootstrap, deflated Sharpe, crash windows, cost stress,
daily-loss risk), parameter maps (descriptive). Writes results/gen96_*.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm
ROOT = Path(__file__).resolve().parents[1]; S = Path(sys.argv[1])
src = open(ROOT / "scripts/gen74_crypto_cfd.py").read().split('SCEN = {')[0]
ns = {"__file__": str(ROOT / "scripts/gen74_crypto_cfd.py")}; exec(compile(src, "gen74_builders", "exec"), ns)
CS, B, CFD, fhp, d2h, R1 = ns["CS"], ns["B"], ns["CFD"], ns["from_hourly_pos"], ns["daily_to_hourly"], ns["R1"]
IDX = R1.index
cw = pd.read_parquet(S / "cstar_full.parquet"); bw = pd.read_parquet(S / "bounce_full.parquet"); wp = pd.read_parquet(S / "weiss_full.parquet")
POS = {"C*": d2h(cw), "Weiss expiry": wp.reindex(IDX).fillna(0.0), "delev bounce": d2h(bw.reindex(columns=CFD).fillna(0.0))}


def book(pos=POS, swap=3.3, mult=1.0, weiss_swap=0.0):
    H = pd.DataFrame({k: fhp(p.loc[:IDX[-1]], weiss_swap if k == "Weiss expiry" else swap, mult) for k, p in pos.items()}).reindex(IDX).fillna(0.0)
    return CS.portfolio_v5(H)[0]


def sh(h, a="2022-01-01", b="2026-09-30"):
    d = h.groupby(h.index.floor("D")).sum().loc[a:b]; return float(d.mean() / d.std() * np.sqrt(365))


base = book(); B0 = sh(base); print("CFD book", round(B0, 3), flush=True)
# ---------------- B: delays (all sleeves executed k hours late) and a deliberate look-ahead control
rows = []
for k in (0, 1, 3, 6, 12, 24):
    h = book({n: p.shift(k).fillna(0.0) for n, p in POS.items()})
    rows.append({"test": f"all sleeves executed {k}h late", "Sharpe 2022-26": sh(h), "TEST": sh(h, "2023", "2024-12-31"), "HOLD": sh(h, "2025", "2026-09-30")})
    print(rows[-1], flush=True)
h = book({n: p.shift(-24).fillna(0.0) for n, p in POS.items()})
rows.append({"test": "CHEAT control: positions 24h EARLY (look-ahead)", "Sharpe 2022-26": sh(h)}); print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen96_delay.csv", index=False)

# ---------------- C: risk
d = base.groupby(base.index.floor("D")).sum().loc["2022":"2026-09-30"]; x = d * 0.15 / (d.std() * np.sqrt(365))
rng = np.random.default_rng(7); n = len(x); bl = 20; shs, dds, cagr = [], [], []
for _ in range(2000):
    st = rng.integers(0, n - bl, n // bl + 1); idx = np.concatenate([np.arange(s, s + bl) for s in st])[:730]
    y = x.to_numpy()[idx]; eq = np.cumprod(1 + y)
    shs.append(y.mean() / y.std() * np.sqrt(365)); dds.append((eq / np.maximum.accumulate(eq) - 1).min()); cagr.append(eq[-1] ** (365 / len(y)) - 1)
risk = {"bootstrap 2y Sharpe p5/p50/p95": np.percentile(shs, [5, 50, 95]).round(2).tolist(),
        "bootstrap 2y max DD p50/p95/p99 (15% vol)": np.percentile(dds, [50, 5, 1]).round(3).tolist(),
        "bootstrap 2y CAGR p5/p50": np.percentile(cagr, [5, 50]).round(3).tolist(), "P(2y return < 0)": float(np.mean(np.array(cagr) < 0))}
sr = x.mean() / x.std(); T = len(x); sk = float(pd.Series(x).skew()); ku = float(pd.Series(x).kurt()) + 3
for N in (30, 700, 7000):
    emax = np.sqrt(1 / T) * ((1 - 0.5772) * norm.ppf(1 - 1 / N) + 0.5772 * norm.ppf(1 - 1 / (N * np.e)))
    risk[f"deflated Sharpe prob (N={N} trials)"] = float(norm.cdf((sr - emax) * np.sqrt(T - 1) / np.sqrt(1 - sk * sr + (ku - 1) / 4 * sr ** 2)))
risk["daily skew"] = sk; risk["daily kurtosis"] = ku; risk["worst day (15% vol)"] = float(x.min()); risk["worst 5 days"] = x.nsmallest(5).round(4).to_dict()
for k, v in risk.items():
    print(k, v, flush=True)
crash = {"LUNA 2022-05-05..20": ("2022-05-05", "2022-05-20"), "3AC/Celsius 2022-06-10..20": ("2022-06-10", "2022-06-20"), "FTX 2022-11-06..15": ("2022-11-06", "2022-11-15"),
         "SVB 2023-03-09..13": ("2023-03-09", "2023-03-13"), "yen carry 2024-08-02..07": ("2024-08-02", "2024-08-07"), "Oct-10 liquidations 2025-10-09..12": ("2025-10-09", "2025-10-12")}
btc = B.panel("close", "1D", ["BTC"])["BTC"]
cr = [{"window": k, "book (15% vol)": float((1 + x.loc[a:b]).prod() - 1), "BTC": float(btc.loc[b] / btc.loc[pd.Timestamp(a) - pd.Timedelta(days=1)] - 1)} for k, (a, b) in crash.items()]
print(pd.DataFrame(cr).round(4).to_string(), flush=True)
st = []
for nm, kw in (("base", {}), ("swap 6.6", {"swap": 6.6}), ("2x spread", {"mult": 2.0}), ("2x spread + swap 6.6", {"mult": 2.0, "swap": 6.6}),
               ("Weiss pays swap too", {"weiss_swap": 3.3})):
    st.append({"cost scenario": nm, "Sharpe 2022-26": sh(book(**kw))}); print(st[-1], flush=True)
hh = base.loc["2022":"2026-09-30 23:00"]; hh = hh * 0.15 / (d.std() * np.sqrt(365))
dl = []
for sc in (1.0, 1.5):
    worst = (hh * sc).groupby(hh.index.floor("D")).apply(lambda g: (np.cumprod(1 + g.to_numpy()).min() - 1))
    dl.append({"scale": sc, "P(intraday dip < -2%)": float((worst < -0.02).mean()), "P(< -3%, the 60% stop at a 5% limit)": float((worst < -0.03).mean()),
               "P(< -5%, FTMO daily limit)": float((worst < -0.05).mean()), "worst intraday dip": float(worst.min())})
    print(dl[-1], flush=True)
yr = x.groupby(x.index.year).apply(lambda y: y.mean() / y.std() * np.sqrt(365)); roll = x.rolling(182).apply(lambda y: y.mean() / y.std() * np.sqrt(365))
print("Sharpe by year", yr.round(2).to_dict(), "| rolling 6m Sharpe min / share < 0:", round(roll.min(), 2), round((roll < 0).mean(), 3), flush=True)
pd.DataFrame([{**{k: str(v) for k, v in risk.items()}, "yearly": str(yr.round(2).to_dict()), "rolling6m_min": roll.min(), "rolling6m_share_neg": (roll < 0).mean()}]).to_csv(ROOT / "results/gen96_risk.csv", index=False)
pd.DataFrame(cr).to_csv(ROOT / "results/gen96_crash.csv", index=False); pd.DataFrame(st).to_csv(ROOT / "results/gen96_costs.csv", index=False)
pd.DataFrame(dl).to_csv(ROOT / "results/gen96_dailyloss.csv", index=False)

# ---------------- D: parameter maps (descriptive, nothing selected)
oi = {}
for c in ("BTC", "ETH"):
    m = B.metrics(c)["sum_open_interest_value"]; oi[c] = (m.where(m > 0).resample("1h").last().ffill(), B.k5(c).close.resample("1h").last())
days = pd.date_range("2021-12-01", "2026-09-30")


def bounce_w(th, hold):
    w = pd.DataFrame(0.0, index=days, columns=CFD); t = days + pd.Timedelta(days=1) - pd.Timedelta(minutes=5)
    for c, (m, px) in oi.items():
        f = lambda s, tt: s.reindex(tt.floor("h"), method="ffill").to_numpy()
        sig = pd.Series((f(m, t) / f(m, t - pd.Timedelta(days=1)) - 1 < -th) & (f(px, t) < f(px, t - pd.Timedelta(days=1))), index=days)
        w[c] = sig.astype(float).rolling(hold, min_periods=1).max() * 0.5
    return w


grid = []
for th in (0.06, 0.08, 0.10, 0.12, 0.14):
    for hold in (1, 2, 3, 4):
        p = d2h(bounce_w(th, hold)); hs = fhp(p, 3.3).reindex(IDX).fillna(0.0)
        grid.append({"OI drop": th, "hold days": hold, "sleeve 2022-26": sh(hs), "book 2022-26": sh(book({**POS, "delev bounce": p}))})
G = pd.DataFrame(grid); G.to_csv(ROOT / "results/gen96_grid_bounce.csv", index=False)
print(G.pivot(index="OI drop", columns="hold days", values="sleeve 2022-26").round(2).to_string(), flush=True)
print(G.pivot(index="OI drop", columns="hold days", values="book 2022-26").round(2).to_string(), flush=True)
raw = CS.cstar_weights().copy(); raw["BNB"] = 0.0; a = raw.abs(); mm = a.where(a > 0).mean(axis=1); cg = []
for thr in (0.0, 0.25, 0.5, 0.75, 1.0):
    w = raw.where(a.ge(mm * thr, axis=0) | (thr == 0), 0.0); p = d2h(w)
    cg.append({"swap-aware thr": thr, "C* 2022-26": sh(fhp(p, 3.3).reindex(IDX).fillna(0.0)), "book 2022-26": sh(book({**POS, "C*": p}))}); print(cg[-1], flush=True)
pd.DataFrame(cg).to_csv(ROOT / "results/gen96_grid_cstar.csv", index=False)
print("done", flush=True)
