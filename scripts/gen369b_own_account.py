"""Gen369b (config/gen369b_protocol.json). Writes results/gen369b.json."""
import json
import itertools
from dataclasses import replace
import numpy as np
import pandas as pd
import stressbook as SB
from qpl.lab import propfirms as PF
g = {"__file__": __file__}; exec(compile(open(SB.ROOT / "scripts/gen369_tail.py").read().split("\nbase = book_positions(False)")[0], "g369", "exec"), g)
base = g["book_positions"](False); hb0 = SB.pnl(base, maker=True); hb2 = SB.pnl(g["cap"](base), maker=True)
src = open(SB.ROOT / "scripts/gen90_books.py").read(); exec(src[src.index("def to_daily_stop"):src.index("P = []")], globals())
HY = PF.PRESETS["HyroTrader Two-Step $200k"]
CFT = replace(PF.PRESETS["Crypto Fund Trader 2-Phase $100k"], name="CFT 2-Phase 200k", account=200000, fee=1200.0, targets=(0.08, 0.05))
v = pd.read_parquet(SB.ROOT / "results/cache_v86_final.parquet")["portfolio"].loc["2022-01-01":SB.END + " 23:00"]
dsh = lambda h: (lambda d: float(d.mean() / d.std() * np.sqrt(365)))(h.groupby(h.index.floor("D")).sum())
unit = lambda h: h * 0.15 / (h.loc["2022":"2024"].groupby(h.loc["2022":"2024"].index.floor("D")).sum().std() * np.sqrt(365))
shift_to = lambda h, tg: h - (h.groupby(h.index.floor("D")).sum().mean() - tg * h.groupby(h.index.floor("D")).sum().std() / np.sqrt(365)) / 24


def frames(h, f, sc, sf, a, z):
    x = h.loc[a:z]; return to_daily_stop(x * sc, 0.5 * f.daily_loss), to_daily_stop(x * sf, 0.5 * f.daily_loss)


def prop(h, f, sc, sf, a, z):
    ch, fd = frames(h, f, sc, sf, a, z)
    pb = PF.pipeline(ch, f, 5, 1, 1.0, 1.0, daily_fd=fd, horizon_days=730, method="bootstrap", n_boot=400, block=20, seed=11)
    return {"net": round(pb["net_mean"]), "p10": round(pb["net_p10"]), "P_profit": round(pb["P_profit"], 3)}


out = {}
for tag, hb in (("T0", hb0), ("T2 cap", hb2)):
    b = unit(hb.reindex(v.index).fillna(0.0))
    for fn, f in (("CFT", CFT), ("HyroTrader", HY)):
        grid = {(sc, sf): prop(b, f, sc, sf, "2022-01-01", "2024-12-31 23:00") for sc, sf in itertools.product((1.0, 1.5, 2.0), (1.0, 1.5))}
        ok = {k: r["net"] for k, r in grid.items() if r["P_profit"] >= 0.9}; ch = max(ok, key=ok.get) if ok else max(grid, key=lambda k: grid[k]["net"])
        r = {"chosen on 2022-24": list(ch), "worst hour": round(float(b.min()), 4)}
        for lvl in ("backtest", "planning"):
            bb = b if lvl == "backtest" else shift_to(b, 0.6 * dsh(b)); r[f"2025-26 {lvl}"] = prop(bb, f, *ch, "2025-01-01", SB.END + " 23:00")
        out[f"{tag} at {fn}"] = r; print(tag, fn, r, flush=True)
# joint: v8.6 at HyroTrader + book at CFT vs v8.6 at HyroTrader + v8.6 at CFT (same bootstrap days)
vu = unit(v)
best = out["T2 cap at CFT"]["chosen on 2022-24"]
for lvl in ("backtest", "planning"):
    va = vu if lvl == "backtest" else shift_to(vu, 1.78); b = unit(hb2.reindex(v.index).fillna(0.0)); bb = b if lvl == "backtest" else shift_to(b, 0.6 * dsh(b))
    accts = {"v8.6 @ HyroTrader": (va, HY, 2.0, 1.5), "v8.6 @ CFT": (va, CFT, 2.0, 1.5), "book @ CFT": (bb, CFT, *best)}
    F = {k: frames(h, f, sc, sf, "2025-01-01", SB.END + " 23:00") for k, (h, f, sc, sf) in accts.items()}
    days = pd.DatetimeIndex(sorted(set.intersection(*[set(x[0].index) for x in F.values()])))
    paths, cal0 = PF._paths(pd.DataFrame(index=days, data={"net": 0.0}), "bootstrap", 730, 1, 400, 20, 11); per_day = len(days) / max(1, cal0[-1]); NET = {}
    for k, (h, f, sc, sf) in accts.items():
        ch_, fd_ = F[k]; ch_, fd_ = ch_.reindex(days).fillna(0.0), fd_.reindex(days).fillna(0.0)
        rc, lo, hi = PF._arrays(ch_, 1.0); rf, lf, hf = PF._arrays(fd_, 1.0); nets = []
        for _, x in paths:
            cal = (np.arange(len(x)) / per_day).astype(int); nets.append(PF._ledger(rc[x], lo[x], hi[x], rf[x], lf[x], hf[x], cal, 0, len(x), f, 5)["net"])
        NET[k] = np.array(nets)
    for combo in (("v8.6 @ HyroTrader", "v8.6 @ CFT"), ("v8.6 @ HyroTrader", "book @ CFT")):
        t = sum(NET[c] for c in combo)
        out[f"joint 2025-26 {lvl}: {' + '.join(combo)}"] = {"mean": round(float(t.mean())), "p10": round(float(np.percentile(t, 10))), "P_loss": round(float((t < 0).mean()), 3),
                                                            "corr of the two accounts": round(float(np.corrcoef(NET[combo[0]], NET[combo[1]])[0, 1]), 3)}
        print(lvl, combo, out[f"joint 2025-26 {lvl}: {' + '.join(combo)}"], flush=True)
json.dump(out, open(SB.ROOT / "results/gen369b.json", "w"), indent=1)
