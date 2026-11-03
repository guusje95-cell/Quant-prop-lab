"""DF-12 (research/v99/df12_protocol.json). Writes results/v99/df12_limit.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
TICK = {"ES": 0.25, "NQ": 0.25}


def study(root):
    d = pd.read_parquet(ROOT / f"research_data/databento/{root}_1m.parquet")
    d = d[d.symbol.str.endswith(".v.0")]; d["ts"] = pd.to_datetime(d.ts_event, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    d = d.drop_duplicates("ts").set_index("ts").sort_index(); t = TICK[root]; res = {}
    for name, (h0, m0, win) in {"entry 18:00": (18, 0, 15), "exit 15:50": (15, 50, 15)}.items():
        starts = d.index[(d.index.hour == h0) & (d.index.minute == m0)]
        cb, cs = [], []
        for s in starts:
            w = d.loc[s:s + pd.Timedelta(minutes=win)]
            if len(w) < 5:
                continue
            ref = w.open.iloc[0]; last = w.close.iloc[-1]
            # buy: limit ref - 1 tick, filled if low <= ref - 2 ticks
            cb.append(-1.0 if (w.low.iloc[:-1] <= ref - 2 * t).any() else (last - ref) / t + 1.0)
            cs.append(-1.0 if (w.high.iloc[:-1] >= ref + 2 * t).any() else (ref - last) / t + 1.0)
        cb, cs = np.array(cb), np.array(cs)
        res[name] = {"n": int(len(cb)), "fill rate buy / sell": [round(float((cb == -1).mean()), 3), round(float((cs == -1).mean()), 3)],
                     "mean cost ticks buy / sell (market = +1)": [round(float(cb.mean()), 3), round(float(cs.mean()), 3)],
                     "median": [float(np.median(cb)), float(np.median(cs))]}
    px = d.close.loc["2023":].mean(); spec = F.SPEC[root]
    comm_bp = F.COMMISSION["micro"] / (px * spec[2]) * 1e4; tick_bp = t / px * 1e4
    avg = np.mean([np.mean(res[k]["mean cost ticks buy / sell (market = +1)"]) for k in res])
    res["per-side cost bp: market / limit (2023-26 prices)"] = [round(tick_bp + comm_bp, 3), round(avg * tick_bp + comm_bp, 3)]
    res["implied cost multiplier"] = round((avg * tick_bp + comm_bp) / (tick_bp + comm_bp), 3)
    return res


out = {r: study(r) for r in ("ES", "NQ")}
out["mean implied multiplier"] = round(float(np.mean([out[r]["implied cost multiplier"] for r in ("ES", "NQ")])), 3)
print(json.dumps(out, indent=1)); (ROOT / "results/v99/df12_limit.json").write_text(json.dumps(out, indent=1))
