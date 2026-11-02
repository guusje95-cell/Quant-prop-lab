"""FPA-4b (research/v99/fpa4b_protocol.json). Writes results/v99/fpa4b_checks.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import fbook


def series(sym):
    x = pd.read_parquet(ROOT / f"research_data/dukascopy/{sym}_1h.parquet")["close"].astype(float)
    x = x[x > 0]; x.index = x.index.tz_localize("UTC").tz_convert("America/New_York").tz_localize(None); return x[~x.index.duplicated()].sort_index()


def leg(x, start_h, end_h, cost):
    """long from the price at start_h ET the evening before (hours after midnight of d-1) to end_h ET on day d"""
    out = {}
    for d in pd.bdate_range("2013-01-02", "2026-09-30"):
        ts = [d - pd.Timedelta(hours=24 - start_h) - pd.Timedelta(hours=1), d + pd.Timedelta(hours=end_h - 1)]
        pos = x.index.searchsorted(ts, side="right") - 1
        if (pos < 0).any() or any((t - x.index[i]) > pd.Timedelta(hours=3) for t, i in zip(ts, pos)):
            continue
        a, b = x.iloc[pos[0]], x.iloc[pos[1]]
        out[d] = b / a - 1 - 2 * cost
    return pd.Series(out)


def main():
    X = {s: series(s) for s in ("XAUUSD", "XAGUSD")}
    Sl = fbook.sleeves(); b0 = fbook.build(Sl)
    f = lambda s, a, z: round(float(s.loc[a:z].mean() / s.loc[a:z].std() * np.sqrt(252)), 3)
    per = lambda b: [f(b, "2010", "2017"), f(b, "2018", "2022"), f(b, "2023", "2026-09-30")]
    ref = per(b0); out = {"futures book without": ref, "variants (book with the sleeve)": {}}
    def book_with(start_h, end_h, cost):
        g = leg(X["XAUUSD"], start_h, end_h, cost); s = leg(X["XAGUSD"], start_h, end_h, cost)
        sl = (g + s.reindex(g.index).fillna(0.0)) / 2; S2 = Sl.copy(); S2["metal overnight"] = sl.reindex(S2.index).fillna(0.0); return per(fbook.build(S2))
    V = {"registered 18 -> 8, 1 bp": (18, 8, 1e-4), "costs 2x": (18, 8, 2e-4), "costs 3x": (18, 8, 3e-4),
         "start 19:00": (19, 8, 1e-4), "start 20:00": (20, 8, 1e-4), "end 07:00": (18, 7, 1e-4), "end 09:00": (18, 9, 1e-4)}
    ok = []
    for k, v in V.items():
        r = book_with(*v); out["variants (book with the sleeve)"][k] = r
        if k != "registered 18 -> 8, 1 bp":
            ok.append(r[2] >= ref[2] + 0.05 and r[0] >= ref[0] and r[1] >= ref[1])
        print(k, r, flush=True)
    yrs = {}
    for s in X:
        on = leg(X[s], 18, 8, 1e-4); yrs[s] = {int(y): round(float(on[on.index.year == y].mean() / on[on.index.year == y].std() * np.sqrt(252)), 2) for y in sorted(set(on.index.year))}
    out["overnight Sharpe by year"] = yrs
    out["split Asian 18->3 / London 3->8 (Sharpe 2013-26)"] = {s: [f(leg(X[s], 18, 3, 1e-4), "2013", "2026"), f(leg(X[s], 3 + 24, 8, 1e-4) if False else leg(X[s], 18, 8, 0) - leg(X[s], 18, 3, 0), "2013", "2026")] for s in X}
    out["verdict"] = {"all 6 stress variants keep +0.05 and no period lower": all(ok), "variants passing": f"{sum(ok)} of {len(ok)}",
                      "years positive (gold / silver, of 14)": [sum(v > 0 for v in yrs["XAUUSD"].values()), sum(v > 0 for v in yrs["XAGUSD"].values())]}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/fpa4b_checks.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
