"""FPA-1b (research/v99/fpa1b_protocol.json): checks of P5 (NR7 + 30-minute opening-range breakout). Writes results/v99/fpa1b_checks.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "scripts/v99"))
import fpa1_price_action as F


def p5(x, nr=7, orm=30, mask=None):
    """NR(nr) + orm-minute opening range breakout; mask: optional set of days to trade instead of the NR days (placebo)"""
    days = sorted(set(x.index.normalize())); out = {}; ranges = []; ok = []
    end_or = (pd.Timestamp("09:30") + pd.Timedelta(minutes=orm - 5)).strftime("%H:%M")
    start = (pd.Timestamp("09:30") + pd.Timedelta(minutes=orm)).strftime("%H:%M")
    for d in days:
        if d.weekday() >= 5:
            continue
        R = x.loc[d:d + pd.Timedelta(hours=23, minutes=59)].between_time("09:30", "15:55")
        if len(R) < 60:
            continue
        cond = (mask is not None and d in mask) or (mask is None and (nr == 0 or (len(ranges) >= nr - 1 and ranges[-1] <= min(ranges[-nr:]))))
        if cond and len(ranges):
            OR = R.between_time("09:30", end_or); hi, lo = OR.high.max(), OR.low.min()
            for t, b in R.between_time(start, "15:50").iterrows():
                if b.close > hi or b.close < lo:
                    side = 1 if b.close > hi else -1
                    r = F.trade(R.loc[t + pd.Timedelta(minutes=5):], side, b.close, lo if side > 0 else hi)
                    if r is not None: out[d] = r
                    break
        ok.append(d); ranges.append((R.high.max() - R.low.min()) / R.close.iloc[-1])
    return pd.Series(out, dtype=float), ok


def book(series):
    bd = pd.bdate_range("2018-01-01", "2026-10-16")
    return sum(s.reindex(bd).fillna(0.0) for s in series) / len(series)


def main():
    X = {m: F.load(m) for m in F.MKTS}; out = {}
    base = {m: p5(X[m]) for m in F.MKTS}; b = book([v[0] for v in base.values()])
    out["P5 NR7 / 30 min"] = [F.sharpe(b, "2018", "2022"), F.sharpe(b, "2023", "2026")]
    u = book([p5(X[m], nr=0)[0] for m in F.MKTS]); out["control: unconditional ORB 30"] = [F.sharpe(u, "2018", "2022"), F.sharpe(u, "2023", "2026")]
    print(out, flush=True)
    rng = np.random.default_rng(7); pl = []
    for i in range(20):
        ser = []
        for m in F.MKTS:
            s, days = base[m]; k = len(s); mask = set(rng.choice(days, size=k, replace=False)) if k else set()
            ser.append(p5(X[m], mask=mask)[0])
        pl.append(F.sharpe(book(ser), "2023", "2026"))
    out["placebo judge (20 random-day draws): p50 / p90 / max"] = [round(float(np.percentile(pl, q)), 3) for q in (50, 90, 100)]
    print(out, flush=True)
    nb = {}
    for nr in (4, 5, 6, 8, 10):
        s = book([p5(X[m], nr=nr)[0] for m in F.MKTS]); nb[f"NR{nr} / 30"] = [F.sharpe(s, "2018", "2022"), F.sharpe(s, "2023", "2026")]
    for orm in (15, 45, 60):
        s = book([p5(X[m], orm=orm)[0] for m in F.MKTS]); nb[f"NR7 / {orm}"] = [F.sharpe(s, "2018", "2022"), F.sharpe(s, "2023", "2026")]
    out["neighbourhood"] = nb; print(nb, flush=True)
    F.COST = 2e-4; c2 = book([p5(X[m])[0] for m in F.MKTS]); F.COST = 1e-4
    out["2x costs"] = [F.sharpe(c2, "2018", "2022"), F.sharpe(c2, "2023", "2026")]
    import fbook
    S = fbook.sleeves(); S["FPA P5"] = b.reindex(S.index).fillna(0.0); bk = fbook.build(S); b0 = fbook.build(fbook.sleeves())
    sh = lambda s, a, z: round(float(s.loc[a:z].mean() / s.loc[a:z].std() * np.sqrt(252)), 3)
    out["futures book (no save)"] = {"without": [sh(b0, "2018", "2022"), sh(b0, "2023", "2026-09-30")], "with P5": [sh(bk, "2018", "2022"), sh(bk, "2023", "2026-09-30")]}
    jd = out["P5 NR7 / 30 min"][1]
    out["verdict"] = {"NR7 beats unconditional": jd > out["control: unconditional ORB 30"][1],
                      "above placebo p90": jd > out["placebo judge (20 random-day draws): p50 / p90 / max"][1],
                      "neighbours judge >= 0.3": f"{sum(v[1] is not None and v[1] >= 0.3 for v in nb.values())} of {len(nb)}",
                      "2x costs judge >= 0.3": out["2x costs"][1] is not None and out["2x costs"][1] >= 0.3}
    print(json.dumps(out, indent=1, default=str)); (ROOT / "results/v99/fpa1b_checks.json").write_text(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
