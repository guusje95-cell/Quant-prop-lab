"""Gen89 (config/gen89_protocol.json): NFP crypto momentum, weekend reversal, equity-trend C* filter, deleveraging bounce.
Writes results/gen89.csv and results/cache_gen89_hourly.parquet."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen74_crypto_cfd.py").read().split('SCEN = {')[0]
ns = {"__file__": str(ROOT / "scripts/gen74_crypto_cfd.py")}; exec(compile(src, "gen74_builders", "exec"), ns)
CS, B, CFD, END, fhp, d2h, R1h = ns["CS"], ns["B"], ns["CFD"], ns["END"], ns["from_hourly_pos"], ns["daily_to_hourly"], ns["R1"]
exec(open(ROOT / "scripts/gen86_bookcheck.py").read().split("C85=pd.read_parquet")[0].split("import crypto_sleeves as CS")[1], globals())
CS.v5_weights = v5w                                                        # 6-event live rule for event sleeves (names starting with E)
IDX = R1h.index; SP, SW = 5.0, 3.3
O = {c: B.k5(c).open.resample("1h").first().loc[:END] for c in ("BTC", "ETH")}
ROWS, CANDS = [], {}


def dsh(h, a, b):
    d = h.groupby(h.index.floor("D")).sum().reindex(pd.date_range(a + "-01-01" if len(a) == 4 else a, b)).fillna(0.0)
    return float(d.mean() / d.std() * np.sqrt(365)) if d.std() > 0 else np.nan


ny = lambda d, h, m=0: (pd.Timestamp(d).tz_localize("America/New_York") + pd.Timedelta(hours=h, minutes=m)).tz_convert("UTC").tz_localize(None)


def book_in(s, t, x):
    if t in s.index:
        s[t] += x


def h1():
    s = pd.Series(0.0, index=IDX)
    k = {c: B.k5(c).open.loc[:END] for c in ("BTC", "ETH")}
    for m in pd.date_range("2020-01-01", "2026-09-01", freq="MS"):
        fri = m + pd.offsets.Week(weekday=4) if m.dayofweek != 4 else m
        t0, t1, tx = ny(fri, 8, 30), ny(fri, 9, 30), ny(fri, 15)
        for c, o in k.items():
            if all(t in o.index for t in (t0, t1, tx)) and o[t1] != o[t0]:
                side = np.sign(o[t1] / o[t0] - 1)
                book_in(s, tx.floor("h"), 0.5 * (side * (o[tx] / o[t1] - 1) - 2 * SP / 1e4))
    return s


def h2():
    s = pd.Series(0.0, index=IDX)
    for sun in pd.date_range("2020-01-05", "2026-09-27", freq="W-SUN"):
        sat = sun - pd.Timedelta(days=1); tx = sun + pd.Timedelta(hours=20)
        for c, o in O.items():
            if all(t in o.index for t in (sat, sun, tx)) and o[sun] != o[sat]:
                side = -np.sign(o[sun] / o[sat] - 1)
                book_in(s, tx, 0.5 * (side * (o[tx] / o[sun] - 1) - 2 * SP / 1e4))
    return s


def h4(th):
    w = pd.DataFrame(0.0, index=pd.date_range("2020-01-01", "2026-09-30"), columns=CFD)
    for c in ("BTC", "ETH"):
        m = B.metrics(c)["sum_open_interest_value"].pipe(lambda z: z.where(z > 0)).resample("1h").last().ffill()
        px = B.k5(c).close.resample("1h").last()
        mid = pd.date_range("2021-12-02", "2026-09-30")
        t = mid - pd.Timedelta(minutes=5)                                 # last values known before 00:00
        oi_now = m.reindex(t.floor("h"), method="ffill").to_numpy(); oi_prev = m.reindex((t - pd.Timedelta(days=1)).floor("h"), method="ffill").to_numpy()
        p_now = px.reindex(t.floor("h"), method="ffill").to_numpy(); p_prev = px.reindex((t - pd.Timedelta(days=1)).floor("h"), method="ffill").to_numpy()
        sig = pd.Series((oi_now / oi_prev - 1 < -th) & (p_now < p_prev), index=mid - pd.Timedelta(days=1))   # row d = decided at close of d
        held = sig.astype(float).rolling(2, min_periods=1).max() * 0.5
        w.loc[held.index, c] = held.to_numpy()
    return fhp(d2h(w), SW)


C85 = pd.read_parquet(ROOT / "results/cache_gen85_hourly.parquet").reindex(IDX).fillna(0.0)
BASE = {"C*": C85["B1 swap-aware C* thr 0.5"], "Weiss expiry": C85["ref Weiss BTC/ETH"]}
bk = lambda cols: CS.portfolio_v5(pd.DataFrame(cols).reindex(IDX).fillna(0.0))[0]
B0 = dsh(bk(BASE), "2022", "2026-09-30"); print("Gen85 CFD book", round(B0, 3), flush=True)
cst = BASE["C*"].groupby(IDX.floor("D")).sum()

for name, fn, primary in (("E H1 NFP-day crypto momentum (PRIMARY)", h1, True), ("E H2 weekend reversal (PRIMARY)", h2, True),
                          ("H4 deleveraging bounce 10% (PRIMARY)", lambda: h4(0.10), True), ("H4 variant 5%", lambda: h4(0.05), False)):
    s = fn().reindex(IDX).fillna(0.0); bA = dsh(bk({**BASE, name: s}), "2022", "2026-09-30")
    dev0 = "2022" if name.startswith("H4") else "2020"
    r = {"test": name, "events/days active": int((s != 0).sum()), "DEV": dsh(s, dev0, "2022-12-31"), "TEST 2023-24": dsh(s, "2023", "2024-12-31"),
         "HOLD 2025-26": dsh(s, "2025", "2026-09-30"), "corr C*": float(pd.concat([cst, s.groupby(IDX.floor("D")).sum()], axis=1).corr().iloc[0, 1]),
         "book before": B0, "book after": bA}
    r["pass"] = bool(primary and r["DEV"] > 0 and r["TEST 2023-24"] >= 0.5 and r["HOLD 2025-26"] >= 0.3 and bA > B0)
    ROWS.append(r); CANDS[name] = s; print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)

# H3 equity-trend filter on C*
us = pd.read_parquet(ROOT / "research_data/dukascopy/US500_1h.parquet").astype("float64"); us = us[~us.index.duplicated()].sort_index()
usd = us.close.resample("1D").last().dropna(); below = (usd < usd.rolling(100).mean())
cw = CS.cstar_weights().copy(); cw["BNB"] = 0.0
a = cw.abs(); m = a.where(a > 0).mean(axis=1); cw = cw.where(a.ge(m * 0.5, axis=0), 0.0)            # Gen85 swap-aware C*
f = pd.Series(np.where(below.reindex(cw.index, method="ffill").fillna(False), 0.5, 1.0), index=cw.index)   # US500 close of d known before d+1 starts
h3 = fhp(d2h(cw.mul(f, axis=0)), SW).reindex(IDX).fillna(0.0)
bA = dsh(bk({**BASE, "C*": h3}), "2022", "2026-09-30")
r = {"test": "H3 US500 trend filter on C* (PRIMARY)", "DEV": dsh(h3, "2020", "2022-12-31"), "TEST 2023-24": dsh(h3, "2023", "2024-12-31"),
     "HOLD 2025-26": dsh(h3, "2025", "2026-09-30"), "C* DEV": dsh(BASE["C*"], "2020", "2022-12-31"), "C* TEST": dsh(BASE["C*"], "2023", "2024-12-31"),
     "C* HOLD": dsh(BASE["C*"], "2025", "2026-09-30"), "book before": B0, "book after": bA}
r["pass"] = bool(r["DEV"] > r["C* DEV"] and r["TEST 2023-24"] > r["C* TEST"] and r["HOLD 2025-26"] > r["C* HOLD"] and bA > B0)
ROWS.append(r); CANDS[r["test"]] = h3; print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
pd.DataFrame(CANDS).to_parquet(ROOT / "results/cache_gen89_hourly.parquet")
pd.DataFrame(ROWS).to_csv(ROOT / "results/gen89.csv", index=False)
print("done", flush=True)
