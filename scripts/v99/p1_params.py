"""v9.9 P1 (research/v99/p1_protocol.json): parameter neighbourhoods of trend 4h, delev bounce and alt kimchi, selected on 2022-24, judged
once on 2025-26. Writes results/v99/p1_params.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import event_live as EL
import alt_kimchi as AK
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a, z):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
def book(H):
    b = unit(CS.portfolio_v5(H)[0]); return {"dev 2022-24": shp(b, "2022", "2024"), "holdout 2025-26": shp(b, "2025", "2026-09-30"), "full": shp(b, "2022", "2026-09-30")}
END = "2026-09-30"


def trend(sets, coins):
    return sum(CS.trend4h(coins=coins, n_in=n, n_out=n // 2) for n in sets) / len(sets)


def delev(th, hold):
    w = CS.delev_bounce_weights(th=th, hold=hold); return CS._from_daily_weights(w, list(w.columns), 5)


def altk(ths):
    ws = [AK.weights(END, th=t) for t in ths]; return sum(CS._from_daily_weights(w, list(w.columns), 5) for w in ws) / len(ws)


GRID = {"trend 4h": {f"{s} {'+BNB/XRP' if len(c) > 3 else 'BTC/ETH/SOL'}": (lambda s=s, c=c: trend(s, c)) for s in ((15, 20, 30), (10, 15, 20), (20, 30, 40), (10, 20, 40))
                     for c in (("BTC", "ETH", "SOL"), ("BTC", "ETH", "SOL", "BNB", "XRP"))},
        "delev bounce": {f"th {t} hold {h}": (lambda t=t, h=h: delev(t, h)) for t in (0.08, 0.10, 0.12, 0.15) for h in (1, 2, 3)},
        "alt kimchi": {str(s): (lambda s=s: altk(s)) for s in ((0.75, 1.0, 1.25), (0.5, 0.75, 1.0), (1.0, 1.25, 1.5), (0.5, 1.0, 1.5))}}
CURRENT = {"trend 4h": "(15, 20, 30) BTC/ETH/SOL", "delev bounce": "th 0.1 hold 2", "alt kimchi": "(0.75, 1.0, 1.25)"}
ref = book(V8); out = {"reference v9.8": ref, "variants": {}, "chosen": {}}
series = {}
for sl, grid in GRID.items():
    out["variants"][sl] = {}
    for name, fn in grid.items():
        p = fn().reindex(idx).fillna(0.0); series[(sl, name)] = p
        out["variants"][sl][name] = book(V8.assign(**{sl: p})); print(sl, name, out["variants"][sl][name], flush=True)
    best = max(grid, key=lambda n: (out["variants"][sl][n]["dev 2022-24"], n == CURRENT[sl]))
    out["chosen"][sl] = best
chg = {sl: series[(sl, n)] for sl, n in out["chosen"].items() if n != CURRENT[sl]}
out["combined chosen"] = book(V8.assign(**chg)) if chg else ref
c = out["combined chosen"]
out["adopt"] = bool(chg and c["holdout 2025-26"] >= ref["holdout 2025-26"] + 0.05 and c["full"] >= ref["full"])
(ROOT / "results/v99/p1_params.json").write_text(json.dumps(out, indent=1)); print(json.dumps({k: out[k] for k in ("reference v9.8", "chosen", "combined chosen", "adopt")}, indent=1))
