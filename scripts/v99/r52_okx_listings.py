"""R52 (research/v99/r52_protocol.json): OKX swap listings of established Binance-perp coins as a sell-the-news sleeve. Writes results/v99/r52_okx_listings.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import event_live as EL
import r16_coinbase as R16
import r30b_checks as RB
import r48_stress as S


def events():
    ev = []
    for f in sorted((ROOT / "research_data/okx_listings").glob("*-USDT-SWAP_1h.parquet")):
        coin = f.name.split("-USDT")[0]
        x = pd.read_parquet(f)
        if not len(x):
            continue
        t0 = pd.DatetimeIndex(x.index).min() if not isinstance(x.index, pd.RangeIndex) else pd.to_datetime(x.iloc[:, 0]).min()
        if not (pd.Timestamp("2022-01-01") <= t0 <= pd.Timestamp("2026-09-23")):
            continue
        for c in (coin, "1000" + coin):
            cl, _ = EL._closes(c)
            if cl is not None:
                if cl.index.min() <= t0 - pd.Timedelta(days=7) and S.on_bybit(c, t0):
                    ev.append((c, t0))
                break
    return sorted(ev, key=lambda e: e[1])


def main():
    idx = S.idx; E = S.per_event()
    def build(extra):
        H = S.V8.copy(); ex = {}
        for k, L in E.items():
            H[S.NAMES[k]] = sum((h for _, _, h, _ in L), pd.Series(0.0, index=idx)); ex[S.NAMES[k]] = sum((g for _, _, _, g in L), pd.Series(0.0, index=idx))
        if extra is not None:
            h, P = RB.venue(extra, idx); H["okx listing short"] = h; ex["okx listing short"] = P.abs().sum(axis=1)
        return S.capped(H, ex)
    base = build(None); OK = events(); used = []
    for c, t in OK:
        _, u = R16.trades({c: t}, idx, "A"); used += u
    R = np.array([u["trade return %"] for u in used]); yrs = pd.to_datetime([u["t"] for u in used]).year
    r = build(OK)
    out = {"v9.9 candidate": base, "events": len(OK), "traded": len(used), "mean trade %": round(float(R.mean()), 2) if len(R) else None,
           "median %": round(float(np.median(R)), 2) if len(R) else None, "by year (n, mean %)": {int(y): [int((yrs == y).sum()), round(float(R[yrs == y].mean()), 2)] for y in sorted(set(yrs))},
           "candidate + okx sleeve": r, "pass": bool(len(used) >= 30 and r[0] >= base[0] + 0.05 and all(r[1][i] >= base[1][i] for i in range(3))),
           "placebo": {f"{d:+d} days": build([(c, t + pd.Timedelta(days=d)) for c, t in OK]) for d in (-60, 60)}}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/r52_okx_listings.json").write_text(json.dumps({**out, "trades": used}, indent=1))


if __name__ == "__main__":
    main()
