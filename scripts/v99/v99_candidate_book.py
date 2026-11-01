"""Backtest series of the v9.9 candidate for the dashboard (Performance -> Backtest): v9.8 + the Coinbase sell-the-news short as a
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

V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
s8, pos8, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8}); SC = 0.902; RISK = 1.5
dd = lambda x: x.groupby(x.index.floor("D")).sum(); kf = lambda x: 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
h, P = RB.venue(list(R16.events().items()), idx); H = V8.assign(**{"venue listing short": h})
def capped(Hx, ev_pos, extra_pos=None):
    ph, W, M = CS.portfolio_v5(Hx); k = kf(ph); m = M.reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
    w = lambda c: W[c].reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
    g = ev_pos.abs().sum(axis=1).reindex(idx).fillna(0.0) * w("listing short") * m * k * RISK
    if extra_pos is not None:
        g = g + extra_pos.abs().sum(axis=1) * w("venue listing short") * m * k * RISK
    kk = (0.045 / g).clip(upper=1.0).fillna(1.0).shift(1).fillna(1.0)
    H2 = Hx.assign(**{"listing short": Hx["listing short"] * kk}); H2 = H2.assign(**{"venue listing short": H2["venue listing short"] * kk}) if extra_pos is not None else H2
    return CS.portfolio_v5(H2)[0]
out = pd.DataFrame({"book": CS.portfolio_v5(H)[0] * SC, "v9.8 book": CS.portfolio_v5(V8)[0] * SC,
                    "book with low-cap cap": capped(H, pos8, P) * SC, "v9.8 with low-cap cap": capped(V8, pos8) * SC,
                    "venue listing short (sleeve)": h}).loc["2022-01-01":"2026-09-30 23:00"].fillna(0.0)
out.to_parquet(ROOT / "results/v99/v99_candidate_book.parquet"); print(out.shape)
