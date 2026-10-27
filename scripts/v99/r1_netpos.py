"""v9.9 R1 helper (copy of the Gen473b position build): saves the v9.8 book's hourly net positions per coin (all sleeves and the
daily sleeves only), the charged backtest cost and the unit book to results/v99/netpos.parquet / netpos_daily.parquet / book_charged.parquet.
Original Gen473b (descriptive audit of v9.8 execution costs): hourly positions of every sleeve (and of every ensemble version / basket
member, which the backtest charges separately), the book's NET position per coin (what the bot actually trades), and the book
Sharpe when the backtest's charged costs are replaced by Bybit costs on the net trades:
  per side = taker 5.5 bp + half spread by coin class (BTC/ETH 0.5, other top-10 1.5, other pack / extra alts 3, event coins 10),
  pessimistic = taker 5.5 + 2x spread + impact (BTC/ETH 1.5, top-10 4, alts 8, event coins 25), maker case = 2 bp + no spread on the
  daily sleeves (limit orders over the first hours), taker elsewhere. Funding stays Binance's. Writes results/gen473b.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import basket_live as BL
import ridge_live as RL
import alt_kimchi as AK
import event_live as EL
from qpl.lab import binance_pack as B, extra_pack as X
END = "2026-09-30"
H = pd.read_parquet(ROOT / "results/v98_paper_sleeves.parquet").drop(columns="port").loc[:END + " 23:00"]
idx = H.index; ix = idx[idx >= "2022-01-01"]
dd = lambda h: h.groupby(h.index.floor("D")).sum()
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
def held(wd):                                                      # daily weights (row d decided at the close of d) -> hourly held
    w = wd.shift(1); return w.reindex(idx.floor("D")).set_axis(idx).fillna(0.0)
C = {}                                                             # sleeve -> list of (unit hourly positions, charged bp)
cw = CS.cstar_pit_weights(); C["C*"] = [(held(cw), 7.5)]
C["trend 4h"] = [(CS.trend4h(n_in=n, n_out=n // 2, positions=True)[1].reindex(idx).fillna(0.0) / 3, 5) for n in (15, 20, 30)]
C["Weiss expiry"] = [(CS.weiss_expiry(positions=True)[1].reindex(idx).fillna(0.0), 5)]
C["delev bounce"] = [(held(CS.delev_bounce_weights()), 5)]
C["ridge ML"] = [(held(RL.ridge_weights(kb=True, volscale=True, spot=True, vrp=True, cal=True)), 5)]
C["alt kimchi"] = [(held(AK.weights(END + " 23:00", th=t)) / 3, 5) for t in (0.75, 1.0, 1.25)]
_, BW = BL.basket(idx); C["diversifier basket"] = [(held(w), 5) for w in BW.values()]
RW = BL.rc_weights(); rc = []
for kind in ("daily", "smooth"):
    rc += [(w.reindex(BL.DAYS).fillna(0.0).shift(1).reindex(idx.floor("D")).set_axis(idx).fillna(0.0) / 6, 5) for w in RW[kind].values()]
for w in RW["h8"].values():
    p = w.copy(); p.index = p.index + pd.Timedelta(hours=8); rc.append((p.reindex(idx, method="ffill").fillna(0.0) / 6, 5))
C["relative crowding 6"] = rc
_, LP, _ = EL.pnl(idx); C["listing short"] = [(LP.reindex(idx).fillna(0.0), 10)]
# book weights: unit-scaled effective weight of each sleeve per hour
ph, W, mult = CS.portfolio_v5(H); k = 0.15 / (dd(ph.loc["2022":"2024"]).std() * np.sqrt(365))
eff = (W.mul(mult.reindex(W.index), axis=0) * k).reindex(ix.floor("D")).set_axis(ix).fillna(0.0)
book = ph.loc["2022":] * k

charged = pd.Series(0.0, index=ix); net = {}; net_daily = {}
DAILY = {"C*", "delev bounce", "ridge ML", "alt kimchi", "diversifier basket"}
for s_, comps in C.items():
    for pos, bp in comps:
        p = pos.reindex(ix).fillna(0.0); t = p.diff().abs().fillna(0.0)
        charged = charged + t.sum(axis=1) * bp / 1e4 * eff[s_]
        part = p.mul(eff[s_], axis=0)
        for c in p.columns:
            net[c] = net.get(c, 0.0) + part[c]
            if s_ in DAILY:
                net_daily[c] = net_daily.get(c, 0.0) + part[c]
N = pd.DataFrame(net).fillna(0.0); ND = pd.DataFrame(net_daily).reindex(columns=N.columns).fillna(0.0)
(ROOT / "results/v99").mkdir(parents=True, exist_ok=True)
N.astype("float32").to_parquet(ROOT / "results/v99/netpos.parquet"); ND.astype("float32").to_parquet(ROOT / "results/v99/netpos_daily.parquet")
pd.DataFrame({"book": book, "charged": charged}).to_parquet(ROOT / "results/v99/book_charged.parquet"); print(N.shape, ND.abs().sum().sum())
