"""v9.9 R50 (research/v99/r50_protocol.json): Binance spot 'Will List' of coins with a >= 7-day-old perp as a separate sell-the-news
sleeve on top of the best candidate. Writes results/v99/r50_will_list.json."""
import json
import re
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
    arts = {}
    for cat in (48, 49, 157, 93):
        f = ROOT / f"research_data/binance_announcements/catalog_{cat}.json"
        if f.exists():
            arts.update({a["id"]: a for a in json.loads(f.read_text(encoding="utf-8"))["articles"]})
    ev = []
    for a in arts.values():
        t = pd.to_datetime(a["releaseDate"], unit="ms"); ti = a["title"]
        if not ti.startswith("Binance Will List") or not (pd.Timestamp("2021-06-01") <= t <= pd.Timestamp("2026-09-23")):
            continue
        for tk in re.findall(r"\(([A-Z0-9]{2,15})\)", ti):
            for c in (tk, "1000" + tk):
                cl, _ = EL._closes(c)
                if cl is not None and cl.index.min() <= t - pd.Timedelta(days=7):
                    T = t.ceil("h") - pd.Timedelta(hours=1)
                    if S.on_bybit(c, T):
                        ev.append((c, T))
                    break
    return sorted(ev, key=lambda x: x[1])


def main():
    idx = S.idx; E = S.per_event()
    def build(extra):
        H = S.V8.copy(); ex = {}
        for k, L in E.items():
            H[S.NAMES[k]] = sum((h for _, _, h, _ in L), pd.Series(0.0, index=idx)); ex[S.NAMES[k]] = sum((g for _, _, _, g in L), pd.Series(0.0, index=idx))
        if extra is not None:
            h, P = RB.venue(extra, idx); H["spot listing short"] = h; ex["spot listing short"] = P.abs().sum(axis=1)
        return S.capped(H, ex)
    base = build(None); WL = events()
    ded, last = {}, {}
    for c, t in WL:
        if c not in last or t - last[c] >= pd.Timedelta(days=7):
            ded[(c, t)] = 1; last[c] = t
    used = []
    for c, t in ded:
        _, u = R16.trades({c: t}, idx, "A"); used += u
    R = np.array([u["trade return %"] for u in used]); yrs = pd.to_datetime([u["t"] for u in used]).year
    r = build(list(ded))
    other = {c for k in ("add", "hodler") for c, _, _, _ in E[k]}
    out = {"best candidate (capped)": base, "events": len(WL), "traded": len(used), "also add / HODLer coins": len({c for c, _ in ded} & other),
           "mean trade %": round(float(R.mean()), 2) if len(R) else None, "median %": round(float(np.median(R)), 2) if len(R) else None,
           "hit rate": round(float((R > 0).mean()), 3) if len(R) else None,
           "by year (n, mean %)": {int(y): [int((yrs == y).sum()), round(float(R[yrs == y].mean()), 2)] for y in sorted(set(yrs))},
           "candidate + spot listing sleeve (capped)": r,
           "pass": bool(len(used) >= 30 and r[0] >= base[0] + 0.05 and all(r[1][i] >= base[1][i] for i in range(3))),
           "placebo": {f"{d:+d} days": build([(c, t + pd.Timedelta(days=d)) for c, t in ded]) for d in (-60, 60)}}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/r50_will_list.json").write_text(json.dumps({**out, "trades": used}, indent=1))


if __name__ == "__main__":
    main()
