"""v9.9 R7 / R7b (research/v99/r7_protocol.json, r7b_protocol.json): short ahead of large token unlocks. Writes results/v99/r7b_unlocks.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import requests
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import event_live as EL
import r16_coinbase as R16
import r22_upbit_r16rules as R22
import r30b_checks as RB
import r32_binance_tag_sleeves as R32
import r34_binance_add as R34
import r42_hodler as R42


def events():
    U = json.loads((ROOT / "research_data/defillama_unlocks/unlocks.json").read_text())
    cg = ROOT / "research_data/defillama_unlocks/coingecko_list.json"
    if not cg.exists():
        cg.write_text(json.dumps(requests.get("https://api.coingecko.com/api/v3/coins/list", timeout=60).json()))
    L = json.loads(cg.read_text()); by_id = {x["id"]: x["symbol"].upper() for x in L}; by_name = {}
    for x in L:
        by_name.setdefault(x["name"].lower(), []).append(x["symbol"].upper())
    ev = []
    for slug, u in U.items():
        cands = [by_id[u["gecko_id"]]] if u.get("gecko_id") in by_id else by_name.get((u.get("name") or "").lower(), [])
        for e in u["events"]:
            t = pd.Timestamp(e["t"], unit="s")
            if not (pd.Timestamp("2021-12-01") <= t <= pd.Timestamp("2026-09-25")) or e["unlocked_before"] <= 0 or e["tokens"] / e["unlocked_before"] < 0.01:
                continue
            for s in cands:
                for c in (s, "1000" + s):
                    cl, _ = EL._closes(c)
                    if cl is not None and cl.index.min() <= t - pd.Timedelta(days=7) and cl.index.max() >= t:
                        ev.append((c, t.normalize(), round(e["tokens"] / e["unlocked_before"] * 100, 2), e["category"])); break
                else:
                    continue
                break
    seen = set(); out = []
    for c, d, pct, cat in sorted(ev, key=lambda x: x[1]):
        if (c, d) not in seen:
            seen.add((c, d)); out.append((c, d, pct, cat))
    return out


def hook_for(E, idx):
    def hook(P, CF):
        P = P.copy()
        for c, d, _, _ in E:
            n = "spo_" + c; start = d - pd.Timedelta(days=7); end = d + pd.Timedelta(days=3)
            cl, fu = EL._closes(c)
            if cl is None:
                continue
            if n in P.columns and (P[n].loc[start:end] != 0).any():
                continue
            cc = cl.loc[start:end]
            if len(cc) == 0:
                continue
            hit = cc[cc >= cc.iloc[0] * 1.30].index; last = hit[0] if len(hit) else cc.index[-1]
            p = pd.Series(-0.05, index=cl.loc[start:last].index); p.index = p.index + pd.Timedelta(hours=1); p = p.reindex(idx).fillna(0.0)
            p = p.where(cl.reindex(idx - pd.Timedelta(hours=1)).notna().to_numpy(), 0.0)
            cur = P[n] if n in P.columns else pd.Series(0.0, index=idx); P[n] = cur.where(cur != 0, p); CF[n] = (cl, fu)
        return P
    return hook


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    book = lambda H: (lambda b: [shp(b, "2022", "2026-09-30"), per(b)])(unit(CS.portfolio_v5(H)[0]))
    ref = book(V8); E = events(); sA, _, _ = EL.pnl(idx, pre_cap=hook_for(E, idx)); hB = sA - s8
    rA = book(V8.assign(**{"listing short": sA})); rB = book(V8.assign(**{"unlock short": hB}))
    yrs = pd.Series([d.year for _, d, _, _ in E]).value_counts().sort_index().to_dict(); cats = pd.Series([c for *_, c in E]).value_counts().to_dict()
    pl = {f"{k:+d} days": book(V8.assign(**{"unlock short": EL.pnl(idx, pre_cap=hook_for([(c, d + pd.Timedelta(days=k), p, ca) for c, d, p, ca in E], idx))[0] - s8})) for k in (-60, 60)}
    hu, _ = RB.venue(list(R16.events().items()) + list(R22.upbit_events().items()), idx); hf, _ = R32.sleeve(R32.events()["futures delisting"], 14, idx)
    ha, _ = RB.venue(list(R34.events().items()), idx); hh, _ = RB.venue(list(R42.events().items()), idx)
    HC = V8.assign(**{"venue listing short": hu, "futures-delisting short": hf, "binance add short": ha, "hodler short": hh})
    out = {"reference v9.8": ref, "unlock events (>= 1%, coin with a perp)": len(E), "by year": {int(k): int(v) for k, v in yrs.items()}, "by category": cats,
           "coins": len({c for c, *_ in E}), "unlock sleeve alone 2022 / 23-24 / 25-26": per(hB),
           "A merged into the event short (R7 as registered)": {"book": rA, "pass": bool(rA[0] >= ref[0] + 0.05 and all(rA[1][i] >= ref[1][i] for i in range(3)))},
           "B separate sleeve": {"book": rB, "pass": bool(rB[0] >= ref[0] + 0.05 and all(rB[1][i] >= ref[1][i] for i in range(3))), "placebo": pl},
           "ALL + add + HODLer": book(HC), "ALL + add + HODLer + unlock sleeve": book(HC.assign(**{"unlock short": hB}))}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/r7b_unlocks.json").write_text(json.dumps({**out, "events": [[c, str(d), p, ca] for c, d, p, ca in E]}, indent=1))


if __name__ == "__main__":
    main()
