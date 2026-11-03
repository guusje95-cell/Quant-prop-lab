"""R54 (research/v99/r54_protocol.json): Weiss expiry luck audit + neighbourhood ensemble in the v9.9 candidate. Writes results/v99/r54_weiss_grid.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import r48_stress as S
from qpl.lab import binance_pack as B


def weiss(pre_h, exit_h, coins=("BTC", "ETH")):
    out = []
    for coin in coins:
        k = B.k5(coin); h = k.close.resample("1h").last().loc[:CS.END]; o = k.open; pnl = pd.Series(0.0, index=h.index)
        days = pd.date_range("2020-01-03", pd.Timestamp(CS.END).normalize(), freq="W-FRI"); days = days[(days + pd.Timedelta(days=7)).month != days.month]
        for d in days:
            ta, t8, tx = d + pd.Timedelta(hours=8 - pre_h), d + pd.Timedelta(hours=8), d + pd.Timedelta(hours=exit_h)
            if not all(t in o.index for t in (ta, t8, tx)) or tx not in pnl.index:
                continue
            pre = o[t8] / o[ta] - 1
            if pre == 0:
                continue
            side = -np.sign(pre); pnl[tx] += side * (o[tx] / o[t8] - 1) - 2 * 5 / 1e4
        out.append(pnl)
    return pd.concat(out, axis=1).fillna(0).mean(axis=1)


def main():
    Ev = S.per_event(); idx = S.idx
    def book(w):
        H = S.V8.copy(); ex = {}; H["Weiss expiry"] = w.reindex(idx).fillna(0.0)
        for k, L in Ev.items():
            H[S.NAMES[k]] = sum((h for _, _, h, _ in L), pd.Series(0.0, index=idx)); ex[S.NAMES[k]] = sum((g for _, _, _, g in L), pd.Series(0.0, index=idx))
        return S.capped(H, ex)
    grid = {}; series = {}
    for pre in (1, 2):
        for ex_h in (9, 10, 11):
            w = weiss(pre, ex_h); series[(pre, ex_h)] = w; grid[f"pre {pre}h, exit {ex_h}:00"] = book(w); print(pre, ex_h, grid[f"pre {pre}h, exit {ex_h}:00"], flush=True)
    vals = np.array([v[0] for v in grid.values()]); chosen = grid["pre 1h, exit 10:00"][0]
    ens = book(sum(series.values()) / len(series)); base = S.capped(S.V8.assign(**{}), {}) if False else None
    ref = grid["pre 1h, exit 10:00"]
    out = {"grid": grid, "chosen percentile": round(float((vals < chosen).mean() * 100)), "grid median minus chosen": round(float(np.median(vals) - chosen), 3),
           "reference (chosen, = v9.9 candidate)": ref, "ensemble of the 6": ens,
           "pass": bool(ens[0] >= ref[0] + 0.05 and all(ens[1][i] >= ref[1][i] for i in range(3)))}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/r54_weiss_grid.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
