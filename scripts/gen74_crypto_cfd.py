"""Gen74 (config/gen74_protocol.json): the crypto sleeves as CFDs at CFD prop firms (spread + swap, no funding, CFD coin list).
Writes results/gen74_sleeves.csv, results/gen74_portfolio.csv, results/gen74_prop.csv, results/cache_gen74_hourly.parquet."""
import sys
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import gen55_firms as G55
from qpl.lab import binance_pack as B
from qpl.lab import propfirms as PF

warnings.filterwarnings("ignore")
END = "2026-09-30 23:00"
CFD = ["BTC", "ETH", "LTC", "XRP", "ADA", "DOGE", "SOL", "DOT", "AVAX", "LINK", "BCH"]
SPREAD = {c: (5.0 if c in ("BTC", "ETH") else 10.0) for c in CFD}
H1 = B.panel("close", "1h", CFD).loc[:END]; R1 = H1.pct_change(fill_method=None).fillna(0.0)
ROLL = pd.Series(R1.index.hour == 21, index=R1.index)                    # the 21:00-22:00 bar is held over the 22:00 rollover


def from_hourly_pos(pos, swap_bp, mult=1.0):
    pos = pos.reindex(R1.index).reindex(columns=CFD).fillna(0.0)
    cost = pd.Series(SPREAD) * mult / 1e4
    turn = pos.diff().abs().fillna(pos.abs()).mul(cost, axis=1).sum(axis=1)
    swap = pos.abs().sum(axis=1).where(ROLL, 0.0) * swap_bp / 1e4
    return (pos * R1).sum(axis=1) - turn - swap


def daily_to_hourly(w):
    """daily weights (row d decided at the close of d) -> hourly positions held during day d+1"""
    w = w.reindex(w.index.append(pd.DatetimeIndex([w.index[-1] + pd.Timedelta(days=1)])))
    held_d = w.reindex(columns=CFD).shift(1)
    return held_d.reindex(R1.index.floor("D")).set_axis(R1.index).fillna(0.0)


def premium_weights_cfd(look=7, hold=7):
    P = B.panel("close", "1D", CFD)
    prem = pd.DataFrame({c: B.premium(c)["close"].resample("1D").mean() for c in CFD}).reindex(P.index).rolling(look).mean()
    listed = P.notna().cumsum() >= 60
    rk = (-prem).where(listed).rank(axis=1, pct=True)
    w = (rk > 2 / 3).astype(float).div((rk > 2 / 3).sum(axis=1), axis=0) - (rk <= 1 / 3).astype(float).div((rk <= 1 / 3).sum(axis=1), axis=0)
    return w.where(pd.Series(np.arange(len(w)) % hold == 0, index=w.index), np.nan).ffill().fillna(0.0)


print("building positions ...", flush=True)
POS = {}
cw = CS.cstar_weights().copy(); cw["BNB"] = 0.0
POS["C*"] = daily_to_hourly(cw)
POS["premium carry"] = daily_to_hourly(premium_weights_cfd())
_, tp = CS.trend4h(positions=True); POS["trend 4h"] = tp.loc[:END]
_, wp = CS.weiss_expiry(positions=True); POS["Weiss expiry"] = wp.loc[:END]


def cascade_cfd(swap_bp, mult=1.0):
    pnl, pos = CS.cascade(limit=0.005, through=0.001, coins=CFD, cost_map={c: SPREAD[c] * mult for c in CFD}, positions=True)
    swap = pos.reindex(R1.index).fillna(0.0).abs().sum(axis=1).where(ROLL, 0.0) * swap_bp / 1e4
    return pnl.reindex(R1.index).fillna(0.0) - swap


def sleeves(swap_bp, mult=1.0):
    out = {s: from_hourly_pos(p, 0.0 if s == "Weiss expiry" else swap_bp, mult) for s, p in POS.items()}
    out["cascade limit strict"] = cascade_cfd(swap_bp, mult)
    return pd.DataFrame(out).fillna(0.0)


def sh(x, a, b):
    y = x.loc[a:b]; d = y.groupby(y.index.floor("D")).sum()
    return float(d.mean() / d.std() * np.sqrt(365)) if d.std() > 0 else np.nan


SCEN = {"swap 0": (0.0, 1.0), "swap 3.3 (base)": (3.3, 1.0), "swap 6.6": (6.6, 1.0), "swap 3.3, 2x spread": (3.3, 2.0)}
ALL = {k: sleeves(*v) for k, v in SCEN.items()}
rows = []
for k, Hs in ALL.items():
    for s in Hs:
        rows.append({"scenario": k, "sleeve": s, "DEV 2020-22": sh(Hs[s], "2020", "2022"), "TEST 2023-24": sh(Hs[s], "2023", "2024"),
                     "HOLD 2025-26": sh(Hs[s], "2025", "2026"), "2022-26": sh(Hs[s], "2022", "2026")})
S = pd.DataFrame(rows); S.to_csv(ROOT / "results/gen74_sleeves.csv", index=False)
pd.set_option("display.width", 200); print(S.round(2).to_string(), flush=True)

base = S[S.scenario == "swap 3.3 (base)"].set_index("sleeve")
keep = [s for s in base.index if base.at[s, "TEST 2023-24"] >= 0.5 and base.at[s, "HOLD 2025-26"] >= 0.3]
print("sleeves kept (rule at base costs):", keep, flush=True)


def stats(ph):
    d = ph.groupby(ph.index.floor("D")).sum(); d = d * 0.15 / (d.std() * np.sqrt(365))
    eq = (1 + d).cumprod(); m = (1 + d).resample("ME").prod() - 1
    return {"Sharpe 2022-26": float(d.mean() / d.std() * np.sqrt(365)), "CAGR @15%": float(eq.iloc[-1] ** (365 / len(d)) - 1),
            "MaxDD": float((eq / eq.cummax() - 1).min()), "pos months": float((m > 0).mean()), "2022": float((1 + d.loc["2022"]).prod() - 1),
            "2025": float((1 + d.loc["2025"]).prod() - 1)}


prow, PORT = [], {}
for k, Hs in ALL.items():
    ph, W, mult = CS.portfolio_v5(Hs[keep])
    ph = ph.loc[:END]; PORT[k] = ph
    prow.append({"scenario": k, "sleeves": "+".join(keep), **stats(ph)})
PT = pd.DataFrame(prow); PT.to_csv(ROOT / "results/gen74_portfolio.csv", index=False); print(PT.round(3).to_string(), flush=True)
pd.DataFrame(PORT).to_parquet(ROOT / "results/cache_gen74_hourly.parquet")


def to_daily_stop(h, stop):
    rows = []
    for d, gg in h.groupby(h.index.floor("D")):
        p = np.cumprod(1 + gg.to_numpy())
        if stop > 0 and (p <= 1 - stop).any():
            k = int(np.argmax(p <= 1 - stop)); close = p[k] - 0.001
            rows.append((d, close - 1, min(p[:k + 1].min(), close) - 1, max(p[:k + 1].max(), 1.0) - 1))
        else:
            rows.append((d, p[-1] - 1, min(p.min(), 1.0) - 1, max(p.max(), 1.0) - 1))
    return pd.DataFrame(rows, columns=["day", "net", "worst", "best"]).set_index("day")


PROP = []
for k in ("swap 3.3 (base)", "swap 6.6"):
    ph = PORT[k]; dd = ph.groupby(ph.index.floor("D")).sum(); ph = ph * 0.15 / (dd.std() * np.sqrt(365))   # 15% vol, as Gen72
    for key in ("FTMO 2-Step $100k", "FundedNext Stellar 2-Step $100k", "BrightFunded Two-Step Classic $100k"):
        f = PF.PRESETS[key]
        for sc, sf in ((0.75, 0.4), (1.0, 0.6)):
            hc = to_daily_stop(ph * sc, 0.5 * f.daily_loss); hf = to_daily_stop(ph * sf, 0.5 * f.daily_loss)
            a = PF.attempts(hc, f, 1.0)
            pb = PF.pipeline(hc, f, 5, 1, 1.0, 1.0, daily_fd=hf, horizon_days=730, method="bootstrap", n_boot=500, block=20, seed=11)
            mi, am = G55.months_with_income(hc, hf, f)
            PROP.append({"scenario": k, "firm": f.name, "risk": f"{sc}/{sf}", "pass": a["P_pass"], "days_to_pass": a["median_days_to_pass"],
                         "boot_net": pb["net_mean"], "boot_p10": pb["net_p10"], "P_profit": pb["P_profit"], "months_with_income": mi})
            print({kk: (round(v, 3) if isinstance(v, float) else v) for kk, v in PROP[-1].items()}, flush=True)
pd.DataFrame(PROP).to_csv(ROOT / "results/gen74_prop.csv", index=False)
print("done", flush=True)
