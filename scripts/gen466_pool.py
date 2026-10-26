"""Gen466 helper: rebuild the hourly P&L of every pool signal from its own (unchanged) script and save results/gen466_pool.parquet."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import basket_live as BL
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
def run(script, cut):
    g = {"__file__": str(ROOT / "scripts" / script)}; exec(compile(open(ROOT / "scripts" / script).read().split(cut)[0], script, "exec"), g); return g
to_h = lambda w: CS._from_daily_weights(w.reindex(BL.DAYS).fillna(0.0), list(w.columns), 5).reindex(idx).fillna(0.0)
P = {}
def add(name, s):
    P[name] = pd.Series(s).reindex(idx).fillna(0.0); print(name, "ok", flush=True)
g = run("gen419_rel_more.py", "\nout = {")
for k, v in g["S"].items():
    add("Gen419 " + k, v)
g = run("gen420_rel_oi_mom.py", "\ndd = lambda h")
add("Gen420 relative OI momentum", g["sl"](g["W"]()))
g = run("gen421_coinm.py", "\nbk0, _ = BL.basket")
add("Gen421 A COIN-M leverage", to_h(g["coinm_lev"]())); add("Gen421 B COIN-M taker divergence", to_h(g["taker_div"]()))
g = run("gen423_depth.py", "\nok = lambda")
add("Gen423 A depth member", g["mA"]); add("Gen423 B relative depth", g["sB"])
g = run("gen434_listing_pace.py", "\nbk0, _ = BL.basket(idx)")
add("Gen434 A listing pace", to_h(g["member"]()))
g = run("gen439_alt_froth.py", "\nls, _, _ = LL.pnl(idx)")
add("Gen439 A funding froth", to_h(g["mk"](g["ZF"])())); add("Gen439 B premium froth", to_h(g["mk"](g["ZP"])()))
g = run("gen440_follow_froth.py", "\nls, _, _ = LL.pnl(idx)")
add("Gen440 follow froth", g["mem_pnl"](g["zser"]()))
g = run("gen444_hl_funding.py", "\nout = {")
for k, v in g["S"].items():
    add("Gen444 " + k, v)
g = run("gen447_rc_pit20.py", "\nb = unit(CS.portfolio_v5(V6")
add("Gen447 relative crowding top-20", g["s"])
g = run("gen457_tron_stables.py", "\nok = lambda")
for k, z in g["SIG"].items():
    add("Gen457 " + k, to_h(g["mk"](z)()))
g = run("gen464_newcoin_rc.py", "\nb = unit(CS.portfolio_v5(V7")
add("Gen464 new-coin crowding", g["s_"])
src = open(ROOT / "scripts/gen414_watchlist.py").read()
g = {"__file__": str(ROOT / "scripts/gen414_watchlist.py")}; exec(compile(src.split("\n# A\n")[0] + "\n" + src.split("# B\n")[1].split("\nbk0, _ = BL.basket")[0], "g414", "exec"), g)
add("Gen414 B CME basis", to_h(g["cme"]()))
g = run("gen429_funding_interval.py", "\nREF_R = ")
add("Gen429 A funding-interval fade", g["sleeve"](7)[0])
y = pd.read_parquet(ROOT / "results/gen406_sleeves_hourly.parquet")
add("Gen406 Y3 Bybit relative crowding 15", y["y3"])
pd.DataFrame(P).to_parquet(ROOT / "results/gen466_pool.parquet"); print("POOL DONE", len(P), flush=True)
