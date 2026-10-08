"""Data-quality validation. Produces a JSON report per processed file."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import loaders
from .sessions import et_minutes, to_et

ROOT = loaders.ROOT
META = ROOT / "data" / "metadata"

TF_MIN = {"M5": 5, "M15": 15, "M30": 30, "H1": 60, "D1": 1440,
          "5min": 5, "15min": 15, "1h": 60, "daily": 1440}


def validate_frame(df: pd.DataFrame, tf: str) -> dict:
    step = pd.Timedelta(minutes=TF_MIN[tf])
    rep: dict = {"rows": int(len(df)), "start": str(df.index[0]), "end": str(df.index[-1])}
    rep["tz"] = str(df.index.tz)
    rep["monotonic"] = bool(df.index.is_monotonic_increasing)
    rep["duplicates"] = int(df.index.duplicated().sum())
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    rep["ohlc_violations"] = int(((h < np.maximum(o, c)) | (l > np.minimum(o, c)) | (h < l)).sum())
    rep["zero_range_bar_frac"] = float(np.mean(h == l))
    # Abnormal moves: |log return| > 12 robust sigmas (MAD-based)
    r = np.diff(np.log(c))
    mad = np.median(np.abs(r - np.median(r))) * 1.4826
    big = np.where(np.abs(r) > 12 * mad)[0] if mad > 0 else np.array([], dtype=int)
    rep["abnormal_moves_gt12mad"] = int(len(big))
    rep["abnormal_examples"] = [
        {"ts": str(df.index[i + 1]), "logret": float(r[i])} for i in big[np.argsort(-np.abs(r[big]))][:8]
    ]
    # Gaps: consecutive timestamps further apart than one bar, excluding weekends.
    dt = np.diff(df.index.asi8) / 1e9 / 60.0
    gaps = np.where(dt > TF_MIN[tf] * 1.01)[0]
    if tf not in ("D1", "daily"):
        e = to_et(df.index)
        wk_gap = []
        long_gaps = []
        for i in gaps:
            a, b = e[i], e[i + 1]
            mins = dt[i]
            if a.dayofweek == 4 and b.dayofweek in (6, 0):
                wk_gap.append(i)
            elif mins > 6 * 60:
                long_gaps.append({"from": str(df.index[i]), "to": str(df.index[i + 1]), "hours": round(mins / 60, 1)})
        rep["gaps_total"] = int(len(gaps))
        rep["weekend_gaps"] = int(len(wk_gap))
        rep["intra_week_gaps_gt_6h"] = len(long_gaps)
        rep["intra_week_gap_examples"] = long_gaps[:15]
        rep["weekend_bars"] = int(((e.dayofweek == 5) | ((e.dayofweek == 6) & (e.hour < 17))).sum())
    # Coverage per year
    yrs = df.index.year
    rep["bars_per_year"] = {int(k): int(v) for k, v in pd.Series(yrs).value_counts().sort_index().items()}
    return rep


def run_all() -> dict:
    logs = loaders.build_processed()
    out = {}
    for key, lg in logs.items():
        source, rest = key.split("/")
        sym, tf = rest.rsplit("_", 1)
        df = loaders.load(source, sym, tf)
        rep = validate_frame(df, tf)
        rep["cleaning"] = lg
        out[key] = rep
    META.mkdir(parents=True, exist_ok=True)
    (META / "data_quality.json").write_text(json.dumps(out, indent=1, default=str))
    return out


def rth_coverage(df: pd.DataFrame, bar_min: int) -> pd.Series:
    """Fraction of expected RTH bars present per ET date (equity indices)."""
    m = et_minutes(df.index)
    rth = (m >= 570) & (m + bar_min <= 960)
    d = to_et(df.index[rth]).normalize()
    return pd.Series(1, index=d).groupby(level=0).sum() / ((960 - 570) / bar_min)


if __name__ == "__main__":
    res = run_all()
    for k, v in res.items():
        print(k, v["rows"], v["start"][:10], v["end"][:10], "dup", v["duplicates"], "ohlc", v["ohlc_violations"],
              "abn", v["abnormal_moves_gt12mad"], "gaps>6h", v.get("intra_week_gaps_gt_6h"), "wkndbars", v.get("weekend_bars"),
              "clean", {kk: vv for kk, vv in v["cleaning"].items() if vv and kk not in ("rows_in", "rows_out")})
