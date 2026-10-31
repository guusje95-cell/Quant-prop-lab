"""v9.9 R16b (robustness of R16 A; diagnostics, no new selection): the Coinbase sell-the-news short run INSIDE event_live.pnl (its gross
cap, Bybit-availability filter, costs; a coin already shorted by v9.8 is skipped), entry one hour later than R16 (T + 2 h); neighbours
hold 3 / 14 days; the HyroTrader total low-cap cap (4.5%, risk 1.5); leave-one-year-out. Writes results/v99/r16b_checks.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import event_live as EL
import r16_coinbase as R16


def hook_for(E, hold_days):
    def hook(P, CF):
        P = P.copy(); added = 0; idx = P.index
        for coin, T in sorted(E.items(), key=lambda e: e[1]):
            n = "spo_" + coin; start = T.floor("h") + pd.Timedelta(hours=2); end = start + pd.Timedelta(days=hold_days)
            cl, fu = EL._closes(coin)
            if cl is None or not ((cl.index >= T.floor("h") - pd.Timedelta(hours=2)) & (cl.index <= start)).any():
                continue
            if n in P.columns and (P[n].loc[T.floor("h"):end] != 0).any():
                continue
            cc = cl.loc[start:end]
            if len(cc) == 0:
                continue
            hit = cc[cc >= cc.iloc[0] * (1 + EL.STOP)].index; last = hit[0] if len(hit) else min(end, cl.index.max())
            p = pd.Series(-EL.SIZE, index=cl.loc[start:last].index); p.index = p.index + pd.Timedelta(hours=1); p = p.reindex(idx).fillna(0.0)
            p = p.where(cl.reindex(idx - pd.Timedelta(hours=1)).notna().to_numpy(), 0.0)
            cur = P[n] if n in P.columns else pd.Series(0.0, index=idx)
            P[n] = cur.where(cur != 0, p); CF[n] = (cl, fu); added += 1
        hook.added = added
        return P
    return hook


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    full = lambda b: [shp(b, "2022", "2026-09-30"), per(b)]
    def capped(s, pos, risk=1.5):
        ph, W, M = CS.portfolio_v5(V7.assign(**{"listing short": s}))
        g = pos.abs().sum(axis=1).reindex(idx).fillna(0.0); w = W["listing short"].reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
        m = M.reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
        k = (0.045 / (g * w * m * 0.902 * risk)).clip(upper=1.0).fillna(1.0).shift(1).fillna(1.0)
        return unit(CS.portfolio_v5(V7.assign(**{"listing short": s * k}))[0])
    s0, pos0, _ = EL.pnl(idx); b0 = unit(CS.portfolio_v5(V7.assign(**{"listing short": s0}))[0]); c0 = capped(s0, pos0)
    E = R16.events(); out = {"reference v9.8": full(b0), "reference v9.8 with the 4.5% low-cap cap (risk 1.5)": full(c0), "variants": {}}
    for hold in (7, 3, 14):
        h = hook_for(E, hold); s, pos, _ = EL.pnl(idx, pre_cap=h); b = unit(CS.portfolio_v5(V7.assign(**{"listing short": s}))[0]); c = capped(s, pos)
        r = {"events used": h.added, "event sleeve 2022 / 23-24 / 25-26": per(s), "book": full(b), "book with low-cap cap": full(c)}
        yrs = {}
        for y in ("2022", "2023", "2024", "2025", "2026"):
            keep = lambda x: x[x.index.year != int(y)]
            yrs["without " + y] = round(shp(keep(b), "2022", "2026-09-30") - shp(keep(b0), "2022", "2026-09-30"), 3)
        r["book gain, leave one year out"] = yrs
        out["variants"][f"hold {hold} days" + (" (registered)" if hold == 7 else " (neighbour)")] = r; print(hold, r, flush=True)
    (ROOT / "results/v99/r16b_checks.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
