"""Gen260 (config/gen260_protocol.json): session-range breakouts on DE40 and US500/US30 CFDs. Writes results/gen260.json."""
import json
import numpy as np
import pandas as pd
import bf2lab as F
out = {}; END = F.END


def run(sym, tz, rng_from, rng_to, scan_to, exit_at, size, cost):
    x = pd.read_parquet(F.ROOT / f"research_data/dukascopy/{sym}_5m.parquet").astype("float64"); x = x[~x.index.duplicated()].sort_index()
    x = x[(x.close > 0)].loc[:END + " 23:55"]
    lt = x.index.tz_localize("UTC").tz_convert(tz); tod = lt.hour * 60 + lt.minute; day = pd.Series(lt.date, index=x.index)
    o, h, l, c = (x[k].to_numpy() for k in ("open", "high", "low", "close"))
    pnl = {}
    for d, ix in pd.Series(np.arange(len(x)), index=x.index).groupby(day.to_numpy()):
        ix = ix.to_numpy(); t = tod[ix]
        if lt[ix[0]].weekday() >= 5:
            continue
        r_ = ix[(t >= rng_from) & (t < rng_to)]; sc = ix[(t >= rng_to) & (t < scan_to)]; ex = ix[t < exit_at]
        if len(r_) < 4 or len(sc) == 0 or len(ex) == 0:
            continue
        hi, lo = h[r_].max(), l[r_].min(); xi = ex[-1]
        for i in sc:
            side = 1 if h[i] > hi else (-1 if l[i] < lo else 0)
            if side:
                ent = max(o[i], hi) if side == 1 else min(o[i], lo)
                if i > xi:
                    break
                t_exit = x.index[xi].floor("h")
                pnl[t_exit] = pnl.get(t_exit, 0.0) + size * (side * (c[xi] / ent - 1) - 2 * cost)
                break
    return pd.Series(pnl, dtype=float)


def evaluate(name, s):
    hb = s.groupby(level=0).sum().reindex(F.IDXbf).fillna(0.0)
    d = s.groupby(s.index.floor("D")).sum(); pre = d.loc["2018":"2019"]
    out[name + " 2018-19"] = round(float(pre.reindex(pd.date_range("2018-01-01", "2019-12-31")).fillna(0).mean() /
                                         pre.reindex(pd.date_range("2018-01-01", "2019-12-31")).fillna(0).std() * np.sqrt(365)), 3)
    r = F.judge(name, hb, out); r["pass"] = bool(r["pass"] and out[name + " 2018-19"] > 0); out[name + " (bf2)"] = r
    print(name, "2018-19", out[name + " 2018-19"], flush=True)
    json.dump(out, open(F.ROOT / "results/gen260.json", "w"), indent=1)


evaluate("A DE40 opening range", run("DE40", "Europe/Berlin", 9 * 60, 9 * 60 + 30, 17 * 60, 17 * 60 + 30, 0.5, 1.5e-4))
evaluate("B US500+US30 pre-market range", run("US500", "America/New_York", 4 * 60, 9 * 60 + 30, 15 * 60 + 55, 16 * 60, 0.25, 1e-4)
         .add(run("US30", "America/New_York", 4 * 60, 9 * 60 + 30, 15 * 60 + 55, 16 * 60, 0.25, 1e-4), fill_value=0.0))
