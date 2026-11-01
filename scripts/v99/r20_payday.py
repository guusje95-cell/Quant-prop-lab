"""v9.9 R20 (research/v99/r20_protocol.json): mid-month payday long in US500 and in BTC/ETH. Writes results/v99/r20_payday.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import event_live as EL
from qpl.lab import binance_pack as B


def paydays(a="2021-11-01", z="2026-10-31"):
    out = []
    for m in pd.date_range(a, z, freq="MS"):
        d = m + pd.Timedelta(days=14)
        d -= pd.Timedelta(days={5: 1, 6: 2}.get(d.dayofweek, 0)); out.append(d)
    return out


def sleeve_us500(idx):
    k = pd.read_parquet(ROOT / "research_data/dukascopy/US500_1h.parquet")["close"]; k.index = pd.DatetimeIndex(k.index).as_unit("ns") + pd.Timedelta(hours=1)
    days = sorted(set(k.index.floor("D"))); last = k.groupby(k.index.floor("D")).apply(lambda s: s.index[-1]); w = pd.Series(0.0, index=k.index)
    for p in paydays():
        prev = [d for d in days if d < p]; nxt = [d for d in days if d >= p]
        if not prev or len(nxt) < 3:
            continue
        a, z = last[prev[-1]], last[nxt[2]]
        w.loc[(w.index > a) & (w.index <= z)] = 1.0                               # held from the close before payday to the +2 close
    r = k.pct_change().fillna(0.0); pos = w.shift(1).fillna(0.0)                  # pos at bar t earns bar t's return (set at the previous close)
    pnl = pos * r - pos.diff().abs().fillna(0.0) * 6.5e-4 - pos.clip(lower=0) * 0.04 / (365 * 24)
    return pnl.groupby(pnl.index.floor("h")).sum().reindex(idx).fillna(0.0)


def sleeve_crypto(idx):
    tot = pd.Series(0.0, index=idx)
    for c in ("BTC", "ETH"):
        cl = B.k5(c).close.resample("1h").last(); cl.index = cl.index + pd.Timedelta(hours=1)
        f = B.funding(c); f.index = pd.DatetimeIndex(f.index).as_unit("ns").floor("h")
        pos = pd.Series(0.0, index=cl.index)
        for p in paydays():
            pos.loc[(pos.index > p - pd.Timedelta(days=1)) & (pos.index <= p + pd.Timedelta(days=2))] = 0.5
        r = cl.pct_change().fillna(0.0); fu = f.groupby(level=0).sum().reindex(cl.index).fillna(0.0)
        pnl = pos * r - pos * fu - pos.diff().abs().fillna(0.0) * 6e-4
        tot = tot.add(pnl.reindex(idx).fillna(0.0), fill_value=0.0)
    return tot


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    b0 = unit(CS.portfolio_v5(V8)[0]); ref = [shp(b0, "2022", "2026-09-30"), per(b0)]; out = {"reference v9.8": ref}
    for name, fn in (("A US500 mid-month payday", sleeve_us500), ("B BTC/ETH mid-month payday", sleeve_crypto)):
        h = fn(idx); b = unit(CS.portfolio_v5(V8.assign(**{name: h}))[0]); r = [shp(b, "2022", "2026-09-30"), per(b)]
        win = h[h != 0]; ev = win.groupby(win.index.to_period("M")).sum()
        out[name] = {"months": len(ev), "mean return per payday window %": round(float(ev.mean() * 100), 3), "share of positive windows": round(float((ev > 0).mean()), 3),
                     "t": round(float(ev.mean() / (ev.std() / np.sqrt(len(ev)))), 2), "sleeve 2022 / 23-24 / 25-26": per(h), "book": r,
                     "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))}
        print(name, out[name], flush=True)
    (ROOT / "results/v99/r20_payday.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
