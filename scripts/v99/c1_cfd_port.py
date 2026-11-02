"""v9.9 C1 (research/v99/c1_protocol.json): v9.8's relative crowding 6 and diversifier basket ported to the BrightFunded crypto-CFD book
(swap-free: no funding; half the measured spread + 1.2 bp per side). Writes results/v99/c1_cfd_port.json."""
import glob
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "src"):
    sys.path.insert(0, str(ROOT / p))
import basket_live as BL
import crypto_sleeves as CS
from qpl.lab import binance_pack as B

C6 = list(BL.C6)
spec = pd.read_csv(sorted(glob.glob(str(ROOT / "research_data/firm_specs/BrightFunded*20261021*.csv")))[-1], encoding="latin1")
meas = {s.split("/")[0].replace("XDG", "DOGE"): float(v) for s, v in zip(spec["symbol"], spec["spread_bp_median"]) if "/USD" in s}
COST = pd.Series({c: (0.5 * meas[c] + 1.2) / 1e4 for c in C6})
dd = lambda x: x.groupby(x.index.floor("D")).sum()
def shp(x, a, z):
    d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
full = lambda x: [shp(x, "2022", "2026-09-30"), per(x)]


def cfd_pnl(pos, R):
    p = pos.reindex(index=R.index, columns=R.columns).fillna(0.0)
    return (p * R).sum(axis=1) - p.diff().abs().fillna(p.abs()).mul(COST.reindex(R.columns), axis=1).sum(axis=1)


def book(H):
    ph, _, _ = CS.portfolio_v5(H); return ph * 0.15 / (dd(ph.loc["2022":"2024"]).std() * np.sqrt(365))


def main():
    BH = pd.read_parquet(ROOT / "results/v99/bf26_sleeves_dump.parquet").drop(columns="port")
    idx = BH.index
    R = B.panel("close", "1h", C6).pct_change(fill_method=None).reindex(idx).fillna(0.0)
    rc = cfd_pnl(BL.rc_positions(idx), R)
    _, W = BL.basket(idx)
    bw = sum(w.reindex(columns=C6).fillna(0.0) for w in W.values())
    days = bw.index.append(pd.DatetimeIndex([bw.index[-1] + pd.Timedelta(days=1)]))
    bpos = bw.reindex(days).shift(1).reindex(idx.floor("D")).set_axis(idx).fillna(0.0)
    bk = cfd_pnl(bpos, R)
    honest = BH.drop(columns=[c for c in ("premium carry", "premium carry BF") if c in BH])
    ref = full(book(honest)); ref26 = full(book(BH))
    v98 = pd.read_parquet(ROOT / "results/v98_paper_sleeves.parquet")["port"]
    corr = lambda s: round(float(pd.concat([dd(s), dd(v98)], axis=1).loc["2022":"2026-09-30"].corr().iloc[0, 1]), 3)
    beats = lambda r, f: bool(r[0] >= f[0] + 0.05 and all(r[1][i] >= f[1][i] for i in range(3)))
    out = {"costs per side bp": (COST * 1e4).round(2).to_dict(), "reference honest bf (no carry)": ref, "bf2.6 (with carry)": ref26,
           "sleeve rc6 CFD": full(rc), "sleeve basket CFD": full(bk), "corr with crypto v9.8 book": {"rc6 CFD": corr(rc), "basket CFD": corr(bk), "honest bf": corr(book(honest))}}
    for name, add in (("A honest bf + rc6 CFD", {"rc6 CFD": rc}), ("B honest bf + basket CFD", {"basket CFD": bk}),
                      ("C honest bf + both", {"rc6 CFD": rc, "basket CFD": bk})):
        r = full(book(honest.assign(**add))); r26 = full(book(BH.assign(**add)))
        out[name] = {"book": r, "pass": beats(r, ref), "on bf2.6 (descriptive)": r26, "bf2.6 strict (descriptive)": beats(r26, ref26),
                     "corr with crypto v9.8": corr(book(honest.assign(**add)))}
        print(name, out[name], flush=True)
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/c1_cfd_port.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
