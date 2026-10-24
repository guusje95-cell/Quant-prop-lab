"""Gen370 (config/gen370_protocol.json). Writes results/gen370.json."""
import json
import sys
from dataclasses import replace
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import propfirms as PF
from qpl.lab import binance_pack as B
src = open(ROOT / "scripts/gen90_books.py").read(); exec(src[src.index("def to_daily_stop"):src.index("P = []")], globals())
END = "2026-09-30"
v = pd.read_parquet(ROOT / "results/cache_v86_final.parquet")["portfolio"].loc["2022-01-01":END + " 23:00"]
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
shift_to = lambda h, tg: h - (dd(h).mean() - tg * dd(h).std() / np.sqrt(365)) / 24
HY = PF.PRESETS["HyroTrader Two-Step $200k"]
CFT = replace(PF.PRESETS["Crypto Fund Trader 2-Phase $100k"], name="CFT 2-Phase 200k", account=200000, fee=1200.0, targets=(0.08, 0.05))
book = pd.read_parquet(ROOT / "results/gen369_book_hourly.parquet")["book"]           # T0 book (Gen369 chosen) -> rebuild the capped version below
g = {"__file__": str(ROOT / "scripts/gen369_tail.py")}; exec(compile(open(ROOT / "scripts/gen369_tail.py").read().split("\nbase = book_positions(False)")[0], "g369", "exec"), g)
import stressbook as SB
capped = SB.pnl(g["cap"](g["book_positions"](False)), maker=True).reindex(v.index).fillna(0.0)
vu = unit(v)


def day_mult(flag_days):
    m = pd.Series(1.0, index=dd(vu).index); m[flag_days.shift(1, fill_value=False).reindex(m.index).fillna(False).to_numpy()] = 0.5
    return m.reindex(vu.index.floor("D")).set_axis(vu.index)


stopday = pd.Series({d: bool(((1 + g_ * 2.0).cumprod() <= 0.975).any()) for d, g_ in vu.groupby(vu.index.floor("D"))})
btc = B.k5("BTC").close.resample("1D").last().pct_change(); bigm = (btc.abs() > 3 * btc.rolling(30).std().shift(1)).reindex(stopday.index).fillna(False)
SERIES = {"P0 baseline": vu, "P2a stop-day brake": vu * day_mult(stopday), "P2b volatility brake": vu * day_mult(bigm)}
for w in (0.1, 0.2, 0.3):
    SERIES[f"P1 capped stress book w {w}"] = unit(vu + w * unit(capped))


def run(h, f, a, z, **kw):
    ff = replace(f, **kw) if kw else f; x = h.loc[a:z]
    pb = PF.pipeline(to_daily_stop(x * 2.0, 0.5 * ff.daily_loss), ff, 5, 1, 1.0, 1.0, daily_fd=to_daily_stop(x * 1.5, 0.5 * ff.daily_loss),
                     horizon_days=730, method="bootstrap", n_boot=400, block=20, seed=11)
    return {"net": round(pb["net_mean"]), "p10": round(pb["net_p10"]), "P_profit": round(pb["P_profit"], 3), "days_to_funded": pb["days_to_funded_median"]}


A, Z = "2022-01-01", "2024-12-31 23:00"
out = {}
for fn, f in (("HyroTrader", HY), ("CFT", CFT)):
    res = {}
    for k, h in SERIES.items():
        res[k] = run(h, f, A, Z)
    res["P2c target brake"] = run(vu, f, A, Z, tgt_brake=0.7, tgt_brake_scale=0.5)
    res["P3 funded cushion"] = run(vu, f, A, Z, cushion_scale=True, cushion_funded_only=True, cushion_min=0.25)
    b0 = res["P0 baseline"]
    win = [k for k, r in res.items() if k != "P0 baseline" and r["P_profit"] >= 0.9 and r["net"] > b0["net"] and r["p10"] >= b0["p10"] * 0.9]
    out[f"{fn} 2022-24"] = res; print(fn, json.dumps(res), "winners", win, flush=True)
    # combination of the winners (series options are exclusive among P1 / P2a / P2b: take the best series winner; engine options stack)
    ser = [k for k in win if k in SERIES]; eng = {}
    if "P2c target brake" in win:
        eng.update(tgt_brake=0.7, tgt_brake_scale=0.5)
    if "P3 funded cushion" in win:
        eng.update(cushion_scale=True, cushion_funded_only=True, cushion_min=0.25)
    hs = SERIES[max(ser, key=lambda k: res[k]["net"])] if ser else vu
    comb = run(hs, f, A, Z, **eng); best_single = max(win, key=lambda k: res[k]["net"]) if win else None
    if best_single and comb["net"] <= res[best_single]["net"]:
        chosen = best_single; hs = SERIES.get(best_single, vu); eng = {}
        if best_single == "P2c target brake":
            eng = dict(tgt_brake=0.7, tgt_brake_scale=0.5)
        if best_single == "P3 funded cushion":
            eng = dict(cushion_scale=True, cushion_funded_only=True, cushion_min=0.25)
    else:
        chosen = ("combination: " + " + ".join(win)) if win else "baseline"
    out[f"{fn} chosen"] = chosen; out[f"{fn} combination 2022-24"] = comb
    for lvl in ("backtest", "planning"):
        hb = vu if lvl == "backtest" else shift_to(vu, 1.78); hc = hs if lvl == "backtest" else shift_to(hs, 1.78 * (dd(hs).mean() / dd(hs).std()) / (dd(vu).mean() / dd(vu).std()))
        out[f"{fn} 2025-26 {lvl}"] = {"baseline": run(hb, f, "2025-01-01", END + " 23:00"), "chosen": run(hc, f, "2025-01-01", END + " 23:00", **eng)}
        print(fn, lvl, chosen, out[f"{fn} 2025-26 {lvl}"], flush=True)
json.dump(out, open(ROOT / "results/gen370.json", "w"), indent=1)
