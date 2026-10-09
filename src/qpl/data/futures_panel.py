"""Daily futures panel from pysystemtrade CSVs (robcarver17/pysystemtrade @bbe29e19, GPL-3; data/futures/*).

Conventions
  * One observation per instrument per calendar date: the LAST print of that date (historic rows are daily,
    recent rows hourly). Timestamps are as published (exchange-agnostic); signals use only same-instrument history.
  * Percentage return r_t = (ADJ_t - ADJ_{t-1}) / PRICE_{t-1}, where ADJ is the back-adjusted series and PRICE the
    actual traded contract price (back-adjusted levels can be far from real prices or negative, so they are never a
    return denominator).
  * Carry yield (annualised) = (PRICE - CARRY) / PRICE / dt, with dt = signed year distance from the priced contract to the
    carry contract (positive carry = backwardation / roll-down in favour of a long).
  * Cost per unit turnover (fraction of notional) = (SpreadCost + PerBlock / Pointsize) / PRICE + Percentage.
    SpreadCost is the repository's per-trade cost estimate in price points (ASSUMPTION: used as-is, stressed 2x/3x).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "data" / "raw" / "ext" / "pysystemtrade" / "data" / "futures"
PROC = ROOT / "data" / "processed" / "futures_panel"


def _yyyymm_years(code: pd.Series) -> pd.Series:
    c = pd.to_numeric(code, errors="coerce")
    y, m = c // 10000, (c // 100) % 100
    return y + (m - 1) / 12.0


def drop_spikes(df: pd.DataFrame, factor: float = 2.5, max_iter: int = 5) -> pd.DataFrame:
    """Remove isolated bad ticks (e.g. decimal shifts): a day whose PRICE (or ADJ change) jumps by >= `factor` versus BOTH
    neighbours in the same direction. Uses t+1 -> data repair only (documented; live paper trading uses DataGuard instead)."""
    lf = np.log(factor)
    for _ in range(max_iter):
        lp = np.log(df.PRICE.where(df.PRICE > 0))
        a, b = lp - lp.shift(1), lp - lp.shift(-1)
        bad = ((a > lf) & (b > lf)) | ((a < -lf) & (b < -lf))
        if not bad.any():
            break
        df = df[~bad.fillna(False)]
    return df


def load_instrument(name: str) -> pd.DataFrame:
    a = pd.read_csv(SRC / "adjusted_prices_csv" / f"{name}.csv", parse_dates=["DATETIME"])
    m = pd.read_csv(SRC / "multiple_prices_csv" / f"{name}.csv", parse_dates=["DATETIME"])
    a["date"] = a.DATETIME.dt.normalize(); m["date"] = m.DATETIME.dt.normalize()
    a = a.groupby("date").last()["price"].rename("adj")
    m = m.sort_values("DATETIME").groupby("date").last()
    df = pd.concat([a, m[["PRICE", "CARRY", "PRICE_CONTRACT", "CARRY_CONTRACT"]]], axis=1).sort_index()
    df = df[df.adj.notna()]
    df["PRICE"] = df["PRICE"].ffill(limit=5)
    df = drop_spikes(df)
    dt = _yyyymm_years(df.CARRY_CONTRACT) - _yyyymm_years(df.PRICE_CONTRACT)
    df["carry_yield"] = ((df.PRICE - df.CARRY) / df.PRICE / dt).where(dt.abs() > 1e-6)
    df["ret"] = df.adj.diff() / df.PRICE.shift(1)
    return df


def build(force: bool = False) -> dict[str, pd.DataFrame]:
    """Returns {'ret','price','carry','cost'} wide DataFrames (dates x instruments) + metadata."""
    PROC.mkdir(parents=True, exist_ok=True)
    keys = ("ret", "price", "carry", "cost")
    if not force and all((PROC / f"{k}.parquet").exists() for k in keys):
        return {k: pd.read_parquet(PROC / f"{k}.parquet") for k in keys}
    cfg = pd.read_csv(SRC / "csvconfig" / "instrumentconfig.csv").set_index("Instrument")
    sc = pd.read_csv(SRC / "csvconfig" / "spreadcosts.csv").set_index("Instrument")["SpreadCost"]
    names = sorted(p.stem for p in (SRC / "adjusted_prices_csv").glob("*.csv") if (SRC / "multiple_prices_csv" / p.name).exists())
    R, Pr, Ca, Co = {}, {}, {}, {}
    for n in names:
        df = load_instrument(n)
        if n not in cfg.index:
            continue
        c = cfg.loc[n]
        per_contract_pts = sc.get(n, np.nan) + (c.PerBlock / c.Pointsize if c.Pointsize else 0)
        R[n], Pr[n], Ca[n] = df.ret, df.PRICE, df.carry_yield
        Co[n] = (per_contract_pts / df.PRICE.abs()) + c.Percentage
    out = {"ret": pd.DataFrame(R), "price": pd.DataFrame(Pr), "carry": pd.DataFrame(Ca), "cost": pd.DataFrame(Co)}
    for k, v in out.items():
        v.index = pd.DatetimeIndex(v.index).as_unit("ns")
        v.sort_index().to_parquet(PROC / f"{k}.parquet")
    return out


def meta() -> pd.DataFrame:
    return pd.read_csv(SRC / "csvconfig" / "instrumentconfig.csv").set_index("Instrument")


def quality(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    r, p = panel["ret"], panel["price"]
    rows = {}
    for n in r.columns:
        x = r[n].dropna()
        if len(x) < 2:
            continue
        pp = p[n].dropna()
        stale = (x == 0).astype(int)
        runs = stale.groupby((stale != stale.shift()).cumsum()).cumsum().max()
        rows[n] = {"start": x.index[0].date(), "end": x.index[-1].date(), "n_days": len(x),
                   "max_gap_days": int(x.index.to_series().diff().dt.days.max()),
                   "abs_ret_gt_25pct": int((x.abs() > 0.25).sum()), "max_abs_ret": float(x.abs().max()),
                   "nonpositive_price_days": int((pp <= 0).sum()), "longest_zero_return_run": int(runs),
                   "ann_vol": float(x.std() * np.sqrt(256)), "median_cost_bp": float(panel["cost"][n].median() * 1e4),
                   "carry_coverage": float(panel["carry"][n].notna().mean())}
    return pd.DataFrame(rows).T


def dedupe(panel: dict[str, pd.DataFrame], min_overlap: int = 500, thresh: float = 0.97) -> tuple[list[str], dict]:
    """Collapse instruments that are the same underlying (mini/micro/duplicate venues): daily-return corr > thresh.
    Groups are formed greedily from the longest histories; each group keeps its CHEAPEST member (lowest median cost),
    ties broken by longer history. Deterministic and uses no performance data."""
    r = panel["ret"]
    q = quality(panel)
    order = q.sort_values(["n_days", "median_cost_bp"], ascending=[False, True]).index.tolist()
    groups: list[list[str]] = []
    for n in order:
        for g in groups:
            ov = r[[n, g[0]]].dropna()
            if len(ov) >= min_overlap and ov[n].corr(ov[g[0]]) > thresh:
                g.append(n); break
        else:
            groups.append([n])
    kept, dropped = [], {}
    for g in groups:
        best = sorted(g, key=lambda n: (q.loc[n, "median_cost_bp"], -q.loc[n, "n_days"]))[0]
        kept.append(best)
        dropped.update({n: best for n in g if n != best})
    return kept, dropped


UNIVERSE_RULES = {
    "asset_classes": ["Equity", "Bond", "FX", "Ags", "Metals", "OilGas", "STIR", "Vol"],
    "exclude_reason": {"Sector/SingleStock": "overlap with equity indices, short histories", "Housing/Weather/Other/CommodityIndex": "illiquid or non-standard",
                       "crypto (BITCOIN/ETHER*)": "crypto data already USED in V4 - excluded to keep the futures test independent"},
    "max_cost_over_vol": 0.01, "max_ann_vol": 1.5, "max_zero_return_run": 60, "min_history_days_for_entry": 256,
}


def universe(panel: dict[str, pd.DataFrame]) -> tuple[list[str], pd.DataFrame]:
    """Pre-registered static instrument filter (config/v6_futures_protocol.json). Uses metadata, costs, vol and data
    quality only - never returns or Sharpe. Point-in-time entry is handled by the strategies (min history)."""
    m, q = meta(), quality(panel)
    kept, _ = dedupe(panel)
    rows = {}
    for n in kept:
        ac = m.loc[n, "AssetClass"] if n in m.index else None
        cost_sr = q.loc[n, "median_cost_bp"] / 1e4 / q.loc[n, "ann_vol"] if q.loc[n, "ann_vol"] > 0 else np.inf
        reasons = []
        if ac not in UNIVERSE_RULES["asset_classes"]:
            reasons.append(f"class {ac}")
        if n.upper().startswith(("BITCOIN", "ETHER")):
            reasons.append("crypto")
        if cost_sr > UNIVERSE_RULES["max_cost_over_vol"]:
            reasons.append(f"cost/vol {cost_sr:.3f}")
        if q.loc[n, "ann_vol"] > UNIVERSE_RULES["max_ann_vol"]:
            reasons.append("broken vol")
        if q.loc[n, "longest_zero_return_run"] > UNIVERSE_RULES["max_zero_return_run"]:
            reasons.append("stale")
        rows[n] = {"asset_class": ac, "cost_over_vol": cost_sr, "included": not reasons, "reasons": "; ".join(reasons)}
    t = pd.DataFrame(rows).T
    return t.index[t.included.astype(bool)].tolist(), t
