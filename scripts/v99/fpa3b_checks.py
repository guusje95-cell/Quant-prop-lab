"""FPA-3b (research/v99/fpa3b_protocol.json). Writes results/v99/fpa3b_checks.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99"):
    sys.path.insert(0, str(ROOT / p))
import fpa1_price_action as F
import fpa1b_checks as B
import fpa3_gold as G


def g3(x, nr=7, orm=30, mask=None):
    days = pd.bdate_range("2018-01-03", "2026-10-16"); out = {}; ranges = []; ok = []
    end_or = (pd.Timestamp("08:20") + pd.Timedelta(minutes=orm - 5)).strftime("%H:%M"); start = (pd.Timestamp("08:20") + pd.Timedelta(minutes=orm)).strftime("%H:%M")
    for d in days:
        R = x.loc[d:d + pd.Timedelta(hours=23, minutes=59)].between_time("08:20", "13:25")
        if len(R) < 50:
            continue
        cond = (mask is not None and d in mask) or (mask is None and (nr == 0 or (len(ranges) >= nr - 1 and ranges[-1] <= min(ranges[-nr:]))))
        if cond and len(ranges):
            OR = R.between_time("08:20", end_or); hi, lo = OR.high.max(), OR.low.min()
            for t, b in R.between_time(start, "13:20").iterrows():
                if b.close > hi or b.close < lo:
                    side = 1 if b.close > hi else -1
                    r = F.trade(R.loc[t + pd.Timedelta(minutes=5):], side, b.close, lo if side > 0 else hi)
                    if r is not None: out[d] = r
                    break
        ok.append(d); ranges.append((R.high.max() - R.low.min()) / R.close.iloc[-1])
    return pd.Series(out, dtype=float), ok


def main():
    x = G.load("America/New_York"); bd = pd.bdate_range("2018-01-01", "2026-10-16"); S = lambda s: s.reindex(bd).fillna(0.0); sh = F.sharpe
    out = {}; base, days = g3(x); jd = sh(S(base), "2023", "2026")
    out["G3"] = [sh(S(base), "2018", "2022"), jd]; u = S(g3(x, nr=0)[0]); out["control unconditional ORB"] = [sh(u, "2018", "2022"), sh(u, "2023", "2026")]
    rng = np.random.default_rng(7); pl = [sh(S(g3(x, mask=set(rng.choice(days, size=len(base), replace=False)))[0]), "2023", "2026") for _ in range(20)]
    out["placebo judge p50 / p90 / max"] = [round(float(np.percentile(pl, q)), 3) for q in (50, 90, 100)]
    nb = {f"NR{n} / 30": [sh(S(g3(x, nr=n)[0]), "2018", "2022"), sh(S(g3(x, nr=n)[0]), "2023", "2026")] for n in (4, 5, 6, 8, 10)}
    nb.update({f"NR7 / {o}": [sh(S(g3(x, orm=o)[0]), "2018", "2022"), sh(S(g3(x, orm=o)[0]), "2023", "2026")] for o in (15, 45, 60)})
    out["neighbourhood"] = nb
    F.COST = 2e-4; c2 = S(g3(x)[0]); F.COST = 1e-4; out["2x costs"] = [sh(c2, "2018", "2022"), sh(c2, "2023", "2026")]
    out["verdict"] = {"beats control": jd > out["control unconditional ORB"][1], "above placebo p90": jd > out["placebo judge p50 / p90 / max"][1],
                      "neighbours judge >= 0.3": f"{sum(v[1] is not None and v[1] >= 0.3 for v in nb.values())} of 8", "2x costs judge >= 0.3": out["2x costs"][1] is not None and out["2x costs"][1] >= 0.3}
    print(out, flush=True)
    P5 = B.book([B.p5(F.load(m))[0] for m in F.MKTS]); comb = (P5 + S(base)) / 2
    out["compression breakout (P5 + G3) stand-alone"] = [sh(comb, "2018", "2022"), sh(comb, "2023", "2026"), "corr P5 vs G3", round(float(P5.corr(S(base))), 3)]
    import fbook
    Sl = fbook.sleeves(); b0 = fbook.build(Sl); Sl["compression breakout"] = comb.reindex(Sl.index).fillna(0.0); b1 = fbook.build(Sl)
    f = lambda s, a, z: round(float(s.loc[a:z].mean() / s.loc[a:z].std() * np.sqrt(252)), 3)
    out["futures book 2018-22 / 2023-26: without / with"] = [[f(b0, "2018", "2022"), f(b0, "2023", "2026-09-30")], [f(b1, "2018", "2022"), f(b1, "2023", "2026-09-30")]]
    ny = G.load("America/New_York"); c = ny.close; on, dy = {}, {}
    for d in bd:
        a, b, e = (G.px_at(c, d + pd.Timedelta(hours=h, minutes=m)) for h, m in ((-6, 0), (8, 20), (17, 0)))
        if np.isfinite([a, b, e]).all():
            on[d] = b / a - 1; dy[d] = e / b - 1
    on, dy = pd.Series(on), pd.Series(dy)
    out["G1 legs: mean return per day in bp, by year (overnight / day)"] = {int(y): [round(float(on[on.index.year == y].mean() * 1e4), 2), round(float(dy[dy.index.year == y].mean() * 1e4), 2)] for y in sorted(set(on.index.year))}
    print(json.dumps(out, indent=1, default=str)); (ROOT / "results/v99/fpa3b_checks.json").write_text(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
