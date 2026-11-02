"""v9.9 R49 (research/v99/r49_protocol.json, FLAGGED): Binance Launchpool / Megadrop tokens as a separate sell-the-news sleeve on top of
the best candidate (R45 Bybit-filtered ALL + add + HODLer, capped). Writes results/v99/r49_launchpool.json."""
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
    ev = {}
    for a in arts.values():
        t = pd.to_datetime(a["releaseDate"], unit="ms"); ti = a["title"]
        if not ("Launchpool" in ti or "Megadrop" in ti) or not (pd.Timestamp("2021-06-01") <= t <= pd.Timestamp("2026-09-23")):
            continue
        for tk in re.findall(r"\(([A-Z0-9]{2,15})\)", ti):
            for c in (tk, "1000" + tk):
                cl, _ = EL._closes(c)
                if cl is None:
                    continue
                first = cl.index[(cl.index >= t.floor("h"))]
                if len(first) and first[0] <= t + pd.Timedelta(hours=72):
                    ev[c] = min(ev.get(c, first[0]), first[0]); break
    return {c: t for c, t in ev.items() if S.on_bybit(c, t)}


def main():
    idx = S.idx; E = S.per_event()
    def build(extra_ev):
        H = S.V8.copy(); ex = {}
        for k, L in E.items():
            s = sum((h for _, _, h, _ in L), pd.Series(0.0, index=idx)); g = sum((gr for _, _, _, gr in L), pd.Series(0.0, index=idx))
            H[S.NAMES[k]] = s; ex[S.NAMES[k]] = g
        if extra_ev is not None:
            h, P = RB.venue(extra_ev, idx); H["launchpool short"] = h; ex["launchpool short"] = P.abs().sum(axis=1)
        return S.capped(H, ex)
    base = build(None); LP = events(); _, used = R16.trades(LP, idx, "A")
    R = np.array([u["trade return %"] for u in used]); yrs = pd.to_datetime([u["t"] for u in used]).year
    hod = {c for c, _, _, _ in E["hodler"]}
    r = build(list(LP.items()))
    out = {"best candidate (capped)": base, "events": len(LP), "traded": len(used), "also HODLer events": len(set(LP) & hod),
           "mean trade %": round(float(R.mean()), 2), "median %": round(float(np.median(R)), 2), "hit rate": round(float((R > 0).mean()), 3),
           "by year (n, mean %)": {int(y): [int((yrs == y).sum()), round(float(R[yrs == y].mean()), 2)] for y in sorted(set(yrs))},
           "candidate + launchpool sleeve (capped)": r,
           "pass": bool(len(used) >= 30 and r[0] >= base[0] + 0.05 and all(r[1][i] >= base[1][i] for i in range(3))),
           "placebo": {f"{d:+d} days": build([(c, t + pd.Timedelta(days=d)) for c, t in LP.items()]) for d in (-60, 60)}}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/r49_launchpool.json").write_text(json.dumps({**out, "trades": used}, indent=1))


if __name__ == "__main__":
    main()
