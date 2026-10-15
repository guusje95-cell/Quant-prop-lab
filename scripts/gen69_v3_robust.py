"""Gen69 (config/gen69_protocol.json) M1, M3, M4 on daily data. Writes results/gen69_robust.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
from qpl.lab import binance_pack as B

day = lambda h: h.groupby(h.index.floor("D")).sum()
D = day(CS.all_sleeves())[["C*", "premium carry", "cascade limit strict"]]
i6 = pd.read_parquet(ROOT / "results/cache_gen64_daily.parquet")["ref I6 4h trend 20/10 BTC/ETH/SOL"]


def expiry(coin):
    k = B.k5(coin); days = pd.date_range("2020-01-03", "2026-09-30", freq="W-FRI")
    days = days[(days + pd.Timedelta(days=7)).month != days.month]; out = {}
    for d in days:
        t7, t8, t10 = d + pd.Timedelta(hours=7), d + pd.Timedelta(hours=8), d + pd.Timedelta(hours=10)
        if t7 not in k.index or t8 not in k.index or t10 not in k.index:
            continue
        o7, o8, o10 = k.open[t7], k.open[t8], k.open[t10]
        c7 = 2 if k.high[t7] >= o7 * 1.0001 else 5; c8 = 2 if k.low[t8] <= o8 * 0.9999 else 5; c10 = 2 if k.high[t10] >= o10 * 1.0001 else 5
        out[d] = -(o8 / o7 - 1) + (o10 / o8 - 1) - (c7 + 2 * c8 + c10) / 1e4
    return pd.Series(out)


k2 = ((expiry("BTC") + expiry("ETH")) / 2).reindex(D.index).fillna(0.0)


def v3(df, look=30, cap=1.5, vt=True):
    z = df.loc["2021-12-01":"2026-09-30"].fillna(0.0); z = z / (z.std() * np.sqrt(365)) * 0.10
    x = z.mean(axis=1); x = x * 0.15 / (x.loc["2022":].std() * np.sqrt(365))
    if vt:
        x = x * (0.15 / (x.rolling(look).std().shift(1) * np.sqrt(365))).clip(upper=cap)
    x = x.loc["2022-01-01":].dropna(); return x * 0.15 / (x.std() * np.sqrt(365))


def summ(x, name):
    eq = (1 + x).cumprod(); m = (1 + x).resample("ME").prod() - 1
    rng = np.random.default_rng(3); a = x.to_numpy(); yrs = []
    for _ in range(2000):
        ii = []
        while len(ii) < 365:
            s0 = rng.integers(len(a)); ii.extend(range(s0, min(s0 + 20, len(a))))
        yrs.append(np.prod(1 + a[np.array(ii[:365])]) - 1)
    r = {"variant": name, "Sharpe": x.mean() / x.std() * np.sqrt(365), "MaxDD": (eq / eq.cummax() - 1).min(), "pos_months": (m > 0).mean(),
         "boot_p5_year": np.percentile(yrs, 5), "P_loss_year": float(np.mean(np.array(yrs) < 0)), "2022": (1 + x.loc["2022"]).prod() - 1}
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True); return r


rows = [summ(v3(D, vt=False), "no vol targeting"), summ(v3(D), "v3 (30d, cap 1.5)")]
rows += [summ(v3(pd.concat([D, i6.rename("i6")], axis=1)), "M1 v3 + 4h trend"), summ(v3(pd.concat([D, k2.rename("k2")], axis=1)), "M1 v3 + expiry window"),
         summ(v3(pd.concat([D, i6.rename("i6"), k2.rename("k2")], axis=1)), "M1 v3 + both")]
for look in (14, 30, 60):
    for cap in (1.25, 1.5, 2.0):
        if (look, cap) != (30, 1.5):
            rows.append(summ(v3(D, look, cap), f"M3 vol target {look}d cap {cap}"))
for K, Hh in ((5, 12), (3, 24), (5, 24)):
    cas = day(CS.cascade(limit=0.005, through=0.001, max_open=K, hold=Hh)).reindex(D.index).fillna(0.0)
    rows.append(summ(v3(pd.concat([D[["C*", "premium carry"]], cas.rename("cas")], axis=1)), f"M4 cascade strict K={K} H={Hh}"))
pd.DataFrame(rows).to_csv(ROOT / "results/gen69_robust.csv", index=False)
