"""v9.9 R39 (research/v99/r39_protocol.json): the event short split into a listing-short and a delisting-short sleeve. Writes results/v99/r39_split_event.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import event_live as EL


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    book = lambda H: (lambda b: [shp(b, "2022", "2026-09-30"), per(b)])(unit(CS.portfolio_v5(H)[0]))
    def keep(pref):
        def hook(P, CF):
            P = P.copy()
            for c in P.columns:
                if c.startswith("spo_") != pref:
                    P[c] = 0.0
            return P
        return hook
    sl, _, _ = EL.pnl(idx, pre_cap=keep(False)); sd, _, _ = EL.pnl(idx, pre_cap=keep(True))
    ref = book(V8); r = book(V7.assign(**{"listing short": sl, "delisting short": sd}))
    out = {"reference v9.8": ref, "listing part 2022 / 23-24 / 25-26": per(sl), "delisting part": per(sd), "event short (both)": per(s8),
           "corr listing vs delisting part": round(float(dd(sl.loc["2022":]).corr(dd(sd.loc["2022":]))), 3),
           "check: parts sum vs event short (daily corr)": round(float(dd(sl + sd).corr(dd(s8))), 4),
           "split": {"book": r, "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))}}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/r39_split_event.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
