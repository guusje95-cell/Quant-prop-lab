"""Backtest series of the v9.9 candidates (incl. ALL = v9.8 + Coinbase/Upbit sleeve + futures-delisting sleeve) for the dashboard (Performance -> Backtest): v9.8 + the Coinbase sell-the-news short as a
separate sleeve (R30), with and without the HyroTrader 4.5% total low-cap cap (risk 1.5), next to v9.8. Same scale as
results/v98_paper_sleeves.parquet ('port' x 0.902). Writes results/v99/v99_candidate_book.parquet."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import event_live as EL
import r30b_checks as RB
import r16_coinbase as R16
import r22_upbit_r16rules as R22
import r32_binance_tag_sleeves as R32
import r34_binance_add as R34

V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
s8, pos8, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8}); SC = 0.902; RISK = 1.5
dd = lambda x: x.groupby(x.index.floor("D")).sum(); kf = lambda x: 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
h, P = RB.venue(list(R16.events().items()), idx); H = V8.assign(**{"venue listing short": h})
def capped(Hx, extra: dict):
    """the 4.5% total low-cap cap (risk 1.5) on the event short plus every extra event sleeve (every coin counted low-cap)"""
    ph, W, M = CS.portfolio_v5(Hx); k = kf(ph); m = M.reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
    w = lambda c: W[c].reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
    g = pos8.abs().sum(axis=1).reindex(idx).fillna(0.0) * w("listing short") * m * k * RISK
    for c, gross in extra.items():
        g = g + gross * w(c) * m * k * RISK
    kk = (0.045 / g).clip(upper=1.0).fillna(1.0).shift(1).fillna(1.0)
    H2 = Hx.copy(); H2["listing short"] = H2["listing short"] * kk
    for c in extra:
        H2[c] = H2[c] * kk
    return CS.portfolio_v5(H2)[0]
hu, Pu = RB.venue(list(R16.events().items()) + list(R22.upbit_events().items()), idx)
hf, _ = R32.sleeve(R32.events()["futures delisting"], 14, idx); gf = (hf != 0).astype(float) * 0.05
H_all = V8.assign(**{"venue listing short": hu, "futures-delisting short": hf})
ha, Pa = RB.venue(list(R34.events().items()), idx); H_add = H_all.assign(**{"binance add short": ha})
out = pd.DataFrame({"book": CS.portfolio_v5(H)[0] * SC, "v9.8 book": CS.portfolio_v5(V8)[0] * SC,
                    "book with low-cap cap": capped(H, {"venue listing short": P.abs().sum(axis=1)}) * SC,
                    "v9.8 with low-cap cap": capped(V8, {}) * SC,
                    "ALL: v9.8 + Coinbase/Upbit + futures delisting": CS.portfolio_v5(H_all)[0] * SC,
                    "ALL with low-cap cap": capped(H_all, {"venue listing short": Pu.abs().sum(axis=1), "futures-delisting short": gf}) * SC,
                    "ALL + Binance add (R34)": CS.portfolio_v5(H_add)[0] * SC,
                    "ALL + Binance add with low-cap cap": capped(H_add, {"venue listing short": Pu.abs().sum(axis=1), "futures-delisting short": gf, "binance add short": Pa.abs().sum(axis=1)}) * SC,
                    "venue listing short (sleeve)": h, "binance add short (sleeve)": ha, "Coinbase+Upbit sleeve": hu, "futures-delisting short (sleeve)": hf}).loc["2022-01-01":"2026-09-30 23:00"].fillna(0.0)
out.to_parquet(ROOT / "results/v99/v99_candidate_book.parquet"); print(out.shape)
