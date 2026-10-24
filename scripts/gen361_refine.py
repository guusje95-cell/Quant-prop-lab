"""Gen361 (config/gen361_protocol.json): cap / sizing / hold refinements of the stress book, chosen on 2020-24. Writes results/gen361.json."""
import json
import numpy as np
import pandas as pd
import stressbook as SB
coins, idx, n = SB.coins, SB.idx, SB.n
btc = SB.D["BTC"]; up = btc > btc.rolling(200).mean()


def nf(cap):
    ev = []
    for j, c in enumerate(coins):
        f = SB.FUND_RAW[c].dropna()
        for ts in f.index[f < -0.001]:
            t = idx.get_indexer([ts.floor("h")])[0]
            if t >= 0:
                ev.append((t, j))
    ev.sort(); P = np.zeros((n, len(coins))); ends = []
    for t, j in ev:
        ends = [e for e in ends if e > t]
        if len(ends) >= cap:
            continue
        P[t:min(t + 24, n), j] = 0.1; ends.append(t + 24)
    return SB.pnl(pd.DataFrame(P, index=idx, columns=coins), maker=True)


def cr(cap):
    sdd = SB.DR.rolling(90, min_periods=60).std().shift(1); mask = (SB.DR < -3 * sdd) & up.reindex(SB.D.index).fillna(False).to_numpy()[:, None]
    return SB.pnl(SB.daily_event_positions(mask, 1.0, 3, max_open=cap), maker=True)


def ps(sizing, hold):
    Z = SB.premium_z(); A = Z.reindex(columns=coins).to_numpy(); P = np.zeros((n, len(coins)))
    for j in range(len(coins)):
        z = np.nan_to_num(A[:, j])
        for t in np.flatnonzero(z < -3):
            s = 0.1 * (min(abs(z[t]) / 3, 2) if sizing == "z" else 1.0)
            P[t + 1:min(t + 1 + hold, n), j] = s
    return SB.pnl(pd.DataFrame(P, index=idx, columns=coins), maker=True)


s24 = lambda S: SB.sh(SB.build(S), "2020", "2024")
cur = {"premium spike": ps("flat", 4), "crash reversal": cr(8), "negative funding": nf(5)}
out = {"start (Gen359)": SB.evaluate(SB.build(cur))}
for key, opts, fn in (("R1 negative funding cap", (5, 10, 20), lambda o: ("negative funding", nf(o))),
                      ("R2 crash reversal cap", (8, 16), lambda o: ("crash reversal", cr(o))),
                      ("R3 premium sizing", ("flat", "z"), lambda o: ("premium spike", ps(o, 4))),
                      ("R4 premium hold", (4, 8), None)):
    res = {}
    for o in opts:
        if fn is None:
            name, h = "premium spike", ps(out["R3 premium sizing chosen"], o)
        else:
            name, h = fn(o)
        trial = {**cur, name: h}; res[str(o)] = (round(s24(trial), 3), trial)
    best = max(res, key=lambda k: res[k][0]); cur = res[best][1]
    out[key] = {k: v[0] for k, v in res.items()}; out[key + " chosen"] = best if key != "R3 premium sizing" else best
    if key == "R3 premium sizing":
        out["R3 premium sizing chosen"] = best
    print(key, out[key], best, flush=True)
bk = SB.build(cur); out["REFINED BOOK"] = SB.evaluate(bk)
print(json.dumps(out["REFINED BOOK"], indent=0))
bk.to_frame("stress book v2").to_parquet(SB.ROOT / "results/gen361_book.parquet")
pd.DataFrame({k: SB.daily(v) for k, v in cur.items()}).to_parquet(SB.ROOT / "results/gen361_sleeves.parquet")
json.dump(out, open(SB.ROOT / "results/gen361.json", "w"), indent=1)
