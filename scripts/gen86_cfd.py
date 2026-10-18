"""Gen86 (config/gen86_protocol.json): CME expiry fade, crypto weekend -> Monday index, pre-FOMC drift on crypto CFDs.
Writes results/gen86.csv and results/cache_gen86_hourly.parquet."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
from qpl.lab import binance_pack as B
FOMC = open(ROOT / "scripts/gen75_cfd.py").read().split('FOMC = """')[1].split('"""')[0].split()
END = "2026-09-30 23:00"
IDX = pd.date_range("2020-01-01", END, freq="1h")
SPREAD, SWAP = 5.0, 3.3
O = {c: B.k5(c).open.resample("1h").first().loc[:END] for c in ("BTC", "ETH")}
ROWS, CANDS = [], {}


def dsh(h, a, b):
    d = h.groupby(h.index.floor("D")).sum().reindex(pd.date_range(a, b if len(b) > 4 else f"{b}-12-31")).fillna(0.0).loc[:"2026-09-30"]
    return float(d.mean() / d.std() * np.sqrt(365)) if d.std() > 0 else np.nan


def rolls(t0, t1):
    return sum(1 for t in pd.date_range(t0.ceil("D") - pd.Timedelta(hours=2), t1, freq="D") if t0 < t <= t1)   # 22:00 UTC crossings


def book_in(s, t, pnl):
    if t in s.index:
        s[t] += pnl


# E1 CME expiry fade
def e1(exit_h):
    s = pd.Series(0.0, index=IDX)
    fr = pd.date_range("2020-01-03", "2026-09-25", freq="W-FRI"); fr = fr[(fr + pd.Timedelta(days=7)).month != fr.month]
    for d in fr:
        lon = lambda h: (pd.Timestamp(d).tz_localize("Europe/London") + pd.Timedelta(hours=h)).tz_convert("UTC").tz_localize(None)
        t15, t16, tx = lon(15), lon(16), lon(exit_h)
        for c in ("BTC", "ETH"):
            o = O[c]
            if not all(t in o.index for t in (t15, t16, tx)):
                continue
            pre = o[t16] / o[t15] - 1
            if pre != 0:
                book_in(s, tx, 0.5 * (-np.sign(pre) * (o[tx] / o[t16] - 1) - 2 * SPREAD / 1e4))
    return s


# E2 crypto weekend -> Monday index
IX = {}
for sym in ("US100", "US500"):
    x = pd.read_parquet(ROOT / f"research_data/dukascopy/{sym}_1h.parquet").astype("float64"); x = x[~x.index.duplicated()].sort_index()
    x.index = pd.DatetimeIndex(x.index).as_unit("ns"); IX[sym] = x.open
btc_c = B.k5("BTC").close.resample("1h").last().loc[:END]


def e2(min_abs):
    s = pd.Series(0.0, index=IDX)
    for fri in pd.date_range("2020-01-03", "2026-09-25", freq="W-FRI"):
        tF = fri + pd.Timedelta(hours=19); tS = fri + pd.Timedelta(days=2, hours=20)     # closes of the 19:00 / Sun 20:00 bars = 20:00 / 21:00
        if tF not in btc_c.index or tS not in btc_c.index:
            continue
        wk = btc_c[tS] / btc_c[tF] - 1
        if abs(wk) <= min_abs or wk == 0:
            continue
        side = np.sign(wk); tX = fri + pd.Timedelta(days=3, hours=20)
        for sym, o in IX.items():
            after = o.loc[fri + pd.Timedelta(days=2, hours=21):tX]
            if len(after) < 5 or after.index[-1] != tX:
                continue
            book_in(s, tX, 0.5 * (side * (o[tX] / after.iloc[0] - 1) - 2 * 1.0 / 1e4))
    return s


# E3 pre-FOMC drift on BTC/ETH
def e3(exit_h):
    s = pd.Series(0.0, index=IDX)
    for ds in FOMC:
        day = pd.Timestamp(ds)
        if day < pd.Timestamp("2020-01-01") or day > pd.Timestamp("2026-09-30"):
            continue
        prev = day - pd.offsets.BDay(1)
        ny = lambda d, h: (d.tz_localize("America/New_York") + pd.Timedelta(hours=h)).tz_convert("UTC").tz_localize(None)
        t0, t1 = ny(prev, 14), ny(day, exit_h)
        for c in ("BTC", "ETH"):
            o = O[c]
            if t0 in o.index and t1 in o.index:
                book_in(s, t1, 0.5 * (o[t1] / o[t0] - 1 - 2 * SPREAD / 1e4 - rolls(t0, t1) * SWAP / 1e4))
    return s


C85 = pd.read_parquet(ROOT / "results/cache_gen85_hourly.parquet"); H83 = pd.read_parquet(ROOT / "results/cache_gen83_hourly.parquet")
S0 = None
BASE = {"C*": C85["B1 swap-aware C* thr 0.5"], "Weiss expiry": C85["ref Weiss BTC/ETH"]}
bk = lambda cols: CS.portfolio_v5(pd.DataFrame(cols).reindex(IDX).fillna(0.0))[0]
B0 = dsh(bk(BASE), "2022", "2026-09-30"); print("Gen85 CFD book 2022-26", round(B0, 3), flush=True)
cst = BASE["C*"].groupby(BASE["C*"].index.floor("D")).sum()

for name, s, primary in (("E1 CME expiry fade, exit 18:00 London (PRIMARY)", e1(18), True), ("E1 variant exit 17:00", e1(17), False),
                         ("E2 crypto weekend -> Monday US100/US500 (PRIMARY)", e2(0.0), True), ("E2 variant |weekend| > 2%", e2(0.02), False),
                         ("E3 pre-FOMC drift BTC/ETH CFD (PRIMARY)", e3(14), True), ("E3 variant exit 16:00 NY", e3(16), False)):
    bA = dsh(bk({**BASE, name: s}), "2022", "2026-09-30")
    r = {"test": name, "events": int((s != 0).sum()), "DEV 2020-22": dsh(s, "2020", "2022"), "TEST 2023-24": dsh(s, "2023", "2024"),
         "HOLD 2025-26": dsh(s, "2025", "2026-09-30"), "hit rate": float((s[s != 0] > 0).mean()), "mean bp/event": float(s[s != 0].mean() * 1e4),
         "corr C*": float(pd.concat([cst, s.groupby(s.index.floor("D")).sum()], axis=1).fillna(0).corr().iloc[0, 1]), "book before": B0, "book after": bA}
    r["pass"] = bool(primary and r["DEV 2020-22"] > 0 and r["TEST 2023-24"] >= 0.5 and r["HOLD 2025-26"] >= 0.3 and bA > B0)
    ROWS.append(r); CANDS[name] = s; print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
pd.DataFrame(CANDS).to_parquet(ROOT / "results/cache_gen86_hourly.parquet")
pd.DataFrame(ROWS).to_csv(ROOT / "results/gen86.csv", index=False)
print("done", flush=True)
