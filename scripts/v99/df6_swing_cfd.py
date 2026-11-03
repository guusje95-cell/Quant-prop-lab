"""DF-6 (deployment, 0 alpha trials, descriptive): the 8 equity-index sleeves held OVERNIGHT (swing, as in the futures book) on index
CFDs that charge swap, vs the daily-flat version. Swap per held night on the net position: long -L% / short -S% a year (/365; Friday ->
Monday = 3 nights), scenarios L/S = 6/1 (typical: financing rate + markup) and 8/2. Positions: scripts/v99/dailyflat_positions.py (same
signals; the swing book weights / level from the swing sleeves). Writes results/v99/df6_swing_cfd.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "scripts/v99"))
import fbook
import futures_db as F0
EQ = ["P1", "R1", "T1", "T2", "FC", "MM", "OIL", "K3"]
S = fbook.sleeves()[EQ]; S = S[S.index.weekday < 5].loc["2010-06-01":"2026-09-30"].fillna(0.0); T = S.loc[:"2022-12-31"]
w = (1 / T.std()).where(T.mean() / T.std() > 0, 0.0); w = w / w.sum()
raw = (S * w).sum(axis=1); lvl = (0.10 / (raw.rolling(60, min_periods=40).std() * np.sqrt(252))).clip(upper=3).shift(1); book = (raw * lvl).dropna()
import dailyflat_positions as DP
pos = DP.session_positions()
net = {}
for r in DP.MK4:
    v = 0.0
    for n in EQ:
        P = pos["R1 from 14:00"] if n == "R1" else pos[n]
        if r in P:
            v = v + P[r].reindex(book.index).fillna(0.0) * w[n]
    net[r] = v * lvl.reindex(book.index).fillna(0.0)
N = pd.DataFrame(net)
nights = pd.Series(np.where(book.index.weekday == 4, 3, 1), index=book.index)
per = lambda b: [round(F0.sharpe(b, *s), 3) for s in F0.SPLITS]
out = {"swing equity book, no swap (futures)": per(book), "daily-flat equity book (DF-3)": [0.258, 0.785, 1.164], "net execution daily-flat (DF-4)": [0.208, 0.895, 1.205],
       "average gross exposure (x equity)": round(float(N.abs().sum(axis=1).mean()), 3), "average net long (x equity)": round(float(N.sum(axis=1).mean()), 3)}
for L, Sh in ((6, 1), (8, 2)):
    drag = (N.clip(lower=0).sum(axis=1) * L / 100 + (-N.clip(upper=0)).sum(axis=1) * Sh / 100) / 365 * nights
    out[f"swing on CFDs, swap {L}% long / {Sh}% short"] = per(book - drag)
print(json.dumps(out, indent=1)); (ROOT / "results/v99/df6_swing_cfd.json").write_text(json.dumps(out, indent=1))
