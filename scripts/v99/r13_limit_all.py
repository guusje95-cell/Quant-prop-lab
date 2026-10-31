"""v9.9 R13 (research/v99/r13_protocol.json): R1 limit orders extended to the remaining net trades (rest of 00:00, 08, 10, 16, other
hours). Same accounting as r1_limit.py. Writes results/v99/r13_limit_all.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import binance_pack as B, extra_pack as X
END = "2026-09-30"
N = pd.read_parquet(ROOT / "results/v99/netpos.parquet"); ND = pd.read_parquet(ROOT / "results/v99/netpos_daily.parquet")
BC = pd.read_parquet(ROOT / "results/v99/book_charged.parquet"); ix = N.index
TOP10 = {"SOL", "XRP", "BNB", "DOGE", "ADA", "TRX", "AVAX", "LINK", "TON", "SUI"}; ALT = set(B.coins()) | set(X.coins())
cls = lambda c: "major" if c in ("BTC", "ETH") else "top10" if c in TOP10 else "alt" if c in ALT else "event"
HS = {"major": 0.5, "top10": 1.5, "alt": 3.0, "event": 10.0}
nt = N.diff().abs().fillna(0.0)
taker = sum(nt[c] * (5.5 + HS[cls(c)]) / 1e4 for c in N.columns)
control = BC["book"] + BC["charged"] - taker
dd = lambda h: h.groupby(h.index.floor("D")).sum()


def stats(h, a="2022", z=END):
    d = dd(h.loc[a:z]); s = lambda a, z: round(float(d.loc[a:z].mean() / d.loc[a:z].std() * np.sqrt(365)), 3)
    return [s(a, z), [s("2022", "2022"), s("2023", "2024"), s("2025", END)]] if a == "2022" and z == END else s(a, z)


dN = N.diff(); mid = ix[ix.hour == 0]
dD0 = ND.diff().loc[mid]; dN0 = dN.loc[mid]
R1X = dD0.where(np.sign(dD0) == np.sign(dN0), 0.0); R1X = np.sign(R1X) * np.minimum(R1X.abs(), dN0.abs())
BUCKETS = {"R1 (daily part of 00:00)": R1X, "B0 rest of 00:00": dN0 - R1X,
           "B8 08:00": dN.loc[ix[ix.hour == 8]], "B10 10:00": dN.loc[ix[ix.hour == 10]], "B16 16:00": dN.loc[ix[ix.hour == 16]],
           "Bx other hours": dN.loc[ix[~ix.hour.isin([0, 8, 10, 16])]]}
coins = [c for c in N.columns if c in B.coins()]
K5 = {c: B.k5(c)[["low", "high", "close"]] for c in coins}


def run(Xb, o=0.0, W=60, delta=1.0, d=0):
    diff = pd.Series(0.0, index=ix); gain = []; n_tr = n_fill = 0
    for c in coins:
        if c not in Xb.columns:
            continue
        k = K5[c]; hs = HS[cls(c)] / 1e4; cl = k["close"]
        for t, x in Xb[c].items():
            if x == 0 or not np.isfinite(x):
                continue
            s = t + pd.Timedelta(minutes=d); bars = k.loc[s:s + pd.Timedelta(minutes=W - 5)]
            pre = cl.loc[:s - pd.Timedelta(minutes=5)]
            if len(bars) == 0 or len(pre) == 0:
                continue
            P0 = pre.iloc[-1]; PW = bars["close"].iloc[-1]; sg = np.sign(x); n_tr += 1
            base = x * (PW / (P0 * (1 + sg * hs)) - 1) - abs(x) * 5.5e-4
            L = P0 * (1 - sg * (hs + o / 1e4))
            hit = bars["low"] <= L * (1 - delta / 1e4) if sg > 0 else bars["high"] >= L * (1 + delta / 1e4)
            if hit.any():
                n_fill += 1; cand = x * (PW / L - 1) - abs(x) * 2e-4
            else:
                cand = -abs(x) * (hs + 5.5e-4)
            h = (s + pd.Timedelta(minutes=W - 5)).floor("h")
            if h in diff.index:
                diff[h] += cand - base; gain.append(((cand - base) / abs(x) * 1e4, t))
    g = pd.Series([a for a, _ in gain], index=pd.DatetimeIndex([b for _, b in gain])) if gain else pd.Series(dtype=float)
    w = lambda s: round(float(s.mean()), 2) if len(s) else None
    return diff, {"orders": n_tr, "fill rate": round(n_fill / max(n_tr, 1), 3), "mean gain bp": w(g),
                  "mean gain bp 2022-24": w(g.loc[:"2024"]), "mean gain bp 2025-26": w(g.loc["2025":])}


def main():
    CEN, CON = dict(o=0, W=60, delta=1, d=0), dict(o=0, W=60, delta=3, d=10)
    out = {"control": stats(control), "buckets": {}}; D = {}
    for name, Xb in BUCKETS.items():
        dc, sc = run(Xb, **CEN); dk, sk = run(Xb, **CON); D[name] = (dc, dk)
        out["buckets"][name] = {"central": sc, "conservative": sk, "control + this bucket": stats(control + dc)}
        print(name, json.dumps(out["buckets"][name]), flush=True)
    ref_c = control + D["R1 (daily part of 00:00)"][0]; ref_k = control + D["R1 (daily part of 00:00)"][1]
    out["reference (control + R1)"] = stats(ref_c)
    chosen = [n for n in BUCKETS if n != "R1 (daily part of 00:00)" and (out["buckets"][n]["central"]["mean gain bp 2022-24"] or 0) > 0
              and (out["buckets"][n]["conservative"]["mean gain bp 2022-24"] or 0) > 0]
    cand_c = ref_c + sum((D[n][0] for n in chosen), pd.Series(0.0, index=ix)); cand_k = ref_k + sum((D[n][1] for n in chosen), pd.Series(0.0, index=ix))
    rc, rr, rk = stats(cand_c), out["reference (control + R1)"], stats(cand_k)
    out["chosen on 2022-24"] = chosen; out["candidate central"] = rc; out["candidate conservative"] = rk; out["reference conservative"] = stats(ref_k)
    out["pass"] = bool(rc[0] >= rr[0] + 0.05 and all(rc[1][i] >= rr[1][i] for i in range(3)) and rk[0] >= out["reference conservative"][0])
    print(json.dumps({k: out[k] for k in ("reference (control + R1)", "chosen on 2022-24", "candidate central", "candidate conservative", "reference conservative", "pass")}), flush=True)
    (ROOT / "results/v99/r13_limit_all.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
