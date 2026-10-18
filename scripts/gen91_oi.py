"""Gen91 (config/gen91_protocol.json): open-interest family. Writes results/gen91.csv and results/cache_gen91_hourly.parquet."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen74_crypto_cfd.py").read().split('SCEN = {')[0]
ns = {"__file__": str(ROOT / "scripts/gen74_crypto_cfd.py")}; exec(compile(src, "gen74_builders", "exec"), ns)
CS, B, CFD, END, fhp, d2h, IDX = ns["CS"], ns["B"], ns["CFD"], ns["END"], ns["from_hourly_pos"], ns["daily_to_hourly"], ns["R1"].index
ROWS, CANDS = [], {}


def dsh(h, a, b):
    d = h.groupby(h.index.floor("D")).sum().reindex(pd.date_range(a, b)).fillna(0.0)
    return float(d.mean() / d.std() * np.sqrt(365)) if d.std() > 0 else np.nan


def oi_weights(coins, oi_sign=-1, px_sign=-1, side=1, th=0.10, hold=2, size=0.5):
    days = pd.date_range("2021-12-01", "2026-09-30"); w = pd.DataFrame(0.0, index=days, columns=list(coins))
    for c in coins:
        try:
            m = B.metrics(c)["sum_open_interest_value"]
        except Exception:
            continue
        m = m.where(m > 0).resample("1h").last().ffill(); px = B.k5(c).close.resample("1h").last()
        t = days + pd.Timedelta(days=1) - pd.Timedelta(minutes=5)
        f = lambda s, tt: s.reindex(tt.floor("h"), method="ffill").to_numpy()
        doi = f(m, t) / f(m, t - pd.Timedelta(days=1)) - 1; dpx = f(px, t) / f(px, t - pd.Timedelta(days=1)) - 1
        sig = pd.Series((oi_sign * doi > th) & (px_sign * dpx > 0), index=days)
        w[c] = sig.astype(float).rolling(hold, min_periods=1).max() * size * side
    return w


per = lambda h: {"DEV 2022": dsh(h, "2022-01-01", "2022-12-31"), "TEST 2023-24": dsh(h, "2023-01-01", "2024-12-31"), "HOLD 2025-26": dsh(h, "2025-01-01", "2026-09-30"),
                 "2022-26": dsh(h, "2022-01-01", "2026-09-30")}
G90 = pd.read_parquet(ROOT / "results/cache_gen90_hourly.parquet")
C85 = pd.read_parquet(ROOT / "results/cache_gen85_hourly.parquet").reindex(IDX).fillna(0.0)
bounce = fhp(d2h(oi_weights(["BTC", "ETH"])), 3.3).reindex(IDX).fillna(0.0)
BASE = {"C*": C85["B1 swap-aware C* thr 0.5"], "Weiss expiry": C85["ref Weiss BTC/ETH"], "delev bounce": bounce}
bk = lambda cols: CS.portfolio_v5(pd.DataFrame(cols).reindex(IDX).fillna(0.0))[0]
B0 = dsh(bk(BASE), "2022-01-01", "2026-09-30"); print("Gen90 CFD book", round(B0, 3), flush=True)
cst = BASE["C*"].groupby(IDX.floor("D")).sum(); bd = bounce.groupby(IDX.floor("D")).sum()
ALTS = [c for c in CFD if c not in ("BTC", "ETH")]
for name, w in (("K1 bounce on CFD altcoins (PRIMARY)", oi_weights(ALTS)),
                ("K2 short-covering fade BTC/ETH (PRIMARY)", oi_weights(["BTC", "ETH"], -1, +1, -1)),
                ("K3 leverage build-up fade BTC/ETH (PRIMARY)", oi_weights(["BTC", "ETH"], +1, +1, -1))):
    h = fhp(d2h(w.reindex(columns=CFD).fillna(0.0)), 3.3).reindex(IDX).fillna(0.0)
    bA = dsh(bk({**BASE, name: h}), "2022-01-01", "2026-09-30"); hd = h.groupby(IDX.floor("D")).sum()
    r = {"test": name, "signals": int((w.diff().fillna(w) > 0).sum().sum() if "fade" not in name else (w.diff().fillna(w) < 0).sum().sum()), **per(h),
         "corr C*": float(pd.concat([cst, hd], axis=1).loc["2022":].corr().iloc[0, 1]), "corr bounce": float(pd.concat([bd, hd], axis=1).loc["2022":].corr().iloc[0, 1]),
         "book before": B0, "book after": bA}
    r["pass"] = bool(r["DEV 2022"] > 0 and r["TEST 2023-24"] >= 0.5 and r["HOLD 2025-26"] >= 0.3 and bA > B0)
    ROWS.append(r); CANDS[name] = h; print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
    if name.startswith("K1"):
        for c in ALTS:
            hc = fhp(d2h(w[[c]].reindex(columns=CFD).fillna(0.0)), 3.3).reindex(IDX).fillna(0.0)
            print("   ", c, {k: round(v, 2) for k, v in per(hc).items()}, flush=True)

# K4 perp route: bounce on 20 coins vs BTC/ETH inside v5
C20 = B.coins()
b2 = CS._from_daily_weights(oi_weights(["BTC", "ETH"]), ["BTC", "ETH"], 5).loc[:END]
b20 = CS._from_daily_weights(oi_weights(C20) * 2 / len(C20), C20, 5).loc[:END]                 # same total budget as 2 coins x 0.5
H5 = CS.v5_sleeves()
v2 = CS.portfolio_v5(pd.concat([H5, b2.rename("delev bounce")], axis=1).fillna(0.0))[0]
v20 = CS.portfolio_v5(pd.concat([H5, b20.rename("delev bounce")], axis=1).fillna(0.0))[0]
p2, p20 = per(b2), per(b20)
r = {"test": "K4 bounce on 20 coins, perp (v5 route)", **p20, "BTC/ETH bounce DEV/TEST/HOLD": f"{p2['DEV 2022']:.2f}/{p2['TEST 2023-24']:.2f}/{p2['HOLD 2025-26']:.2f}",
     "v6 (BTC/ETH)": dsh(v2, "2022-01-01", "2026-09-30"), "v6 (20 coins)": dsh(v20, "2022-01-01", "2026-09-30")}
r["pass"] = bool(all(p20[k] > p2[k] for k in ("DEV 2022", "TEST 2023-24", "HOLD 2025-26")) and r["v6 (20 coins)"] > r["v6 (BTC/ETH)"])
ROWS.append(r); CANDS[r["test"]] = b20.reindex(IDX).fillna(0.0); print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
pd.DataFrame(CANDS).to_parquet(ROOT / "results/cache_gen91_hourly.parquet")
pd.DataFrame(ROWS).to_csv(ROOT / "results/gen91.csv", index=False)
print("done", flush=True)
