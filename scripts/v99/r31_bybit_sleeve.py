"""v9.9 R31 (research/v99/r31_protocol.json): Bybit perp-delisting shorts as a separate sleeve. Writes results/v99/r31_bybit_sleeve.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/hub_research", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import event_live as EL
import bybit_event_shorts as BE


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, pos8, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    book = lambda H: (lambda b: [shp(b, "2022", "2026-09-30"), per(b)])(unit(CS.portfolio_v5(H)[0]))
    ref = book(V8); E = BE.events(BE.ANN)["B"]; out = {"reference v9.8": ref, "events": len(E)}
    def extra(ev):
        s, pos, _ = EL.pnl(idx, pre_cap=BE.make_hook(ev, idx)); return s - s8
    h = extra(E); out["sleeve 2022 / 23-24 / 25-26"] = per(h); out["corr with event short"] = round(float(dd(h.loc["2022":]).corr(dd(s8.loc["2022":]))), 3)
    r = book(V8.assign(**{"bybit delisting short": h})); out["book"] = r; out["pass"] = bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))
    out["placebo"] = {f"{d:+d} days": book(V8.assign(**{"bybit delisting short": extra([(c, t + pd.Timedelta(days=d)) for c, t in E])})) for d in (-60, 60)}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/r31_bybit_sleeve.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
