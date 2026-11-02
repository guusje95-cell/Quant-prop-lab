"""FPA-4 (research/v99/fpa4_protocol.json, FLAGGED): metal overnight drift, judged on unseen data (gold 2013-17, silver).
Writes results/v99/fpa4_metal_overnight.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
COST = 1e-4


def legs(sym):
    x = pd.read_parquet(ROOT / f"research_data/dukascopy/{sym}_1h.parquet")["close"].astype(float)
    x = x[x > 0]; x.index = x.index.tz_localize("UTC").tz_convert("America/New_York").tz_localize(None); x = x[~x.index.duplicated()].sort_index()
    on, dy = {}, {}
    for d in pd.bdate_range("2013-01-02", "2026-09-30"):
        a = x.get(d - pd.Timedelta(hours=7)); b = x.get(d + pd.Timedelta(hours=7)); e = x.get(d + pd.Timedelta(hours=16))   # bar starts 17:00 prev, 07:00, 16:00
        if a is not None and b is not None and e is not None and np.isfinite([a, b, e]).all():
            on[d] = b / a - 1 - 2 * COST; dy[d] = e / b - 1
    return pd.Series(on), pd.Series(dy)


def sh(s, a, z):
    s = s.loc[a:z]; return round(float(s.mean() / s.std() * np.sqrt(252)), 3) if len(s) > 50 and s.std() > 0 else None


def main():
    out = {}; S = {}
    for sym in ("XAUUSD", "XAGUSD"):
        on, dy = legs(sym); bh = on + dy; sp = on - dy - 2 * COST; S[sym] = on
        out[sym] = {w: {"overnight": sh(on, a, z), "spread overnight-day": sh(sp, a, z), "buy-and-hold": sh(bh, a, z), "days": int(len(on.loc[a:z]))}
                    for w, (a, z) in {"2013-17": ("2013", "2017"), "2018-22": ("2018", "2022"), "2023-26": ("2023", "2026"), "2013-26": ("2013", "2026")}.items()}
    A = out["XAUUSD"]["2013-17"]; B = out["XAGUSD"]["2013-26"]
    out["A gold 2013-17 pass"] = bool(A["overnight"] is not None and A["overnight"] >= 0.5 and A["spread overnight-day"] > 0)
    out["B silver 2013-26 pass"] = bool(B["overnight"] is not None and B["overnight"] >= 0.3 and B["spread overnight-day"] > 0)
    import fbook
    Sl = fbook.sleeves(); b0 = fbook.build(Sl); sleeve = ((S["XAUUSD"] + S["XAGUSD"].reindex(S["XAUUSD"].index).fillna(0.0)) / 2)
    Sl["metal overnight"] = sleeve.reindex(Sl.index).fillna(0.0); b1 = fbook.build(Sl)
    f = lambda s, a, z: round(float(s.loc[a:z].mean() / s.loc[a:z].std() * np.sqrt(252)), 3)
    out["futures book 2010-17 / 2018-22 / 2023-26: without / with"] = [[f(b0, "2010", "2017"), f(b0, "2018", "2022"), f(b0, "2023", "2026-09-30")],
                                                                     [f(b1, "2010", "2017"), f(b1, "2018", "2022"), f(b1, "2023", "2026-09-30")]]
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/fpa4_metal_overnight.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
