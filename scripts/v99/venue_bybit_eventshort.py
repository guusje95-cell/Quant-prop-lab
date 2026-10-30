"""v9.9 V1 (descriptive, no trials): the event short priced on BYBIT instead of Binance. The Hyro platform trades on live Bybit market data,
so the live event short earns Bybit price moves and pays Bybit funding. For every event-short position whose active hours are covered by
research_data/bybit_listings (first 40 days after the Bybit listing, hourly close + funding), the Binance close / funding is replaced by
Bybit's; other positions keep Binance (reported as coverage). Writes results/v99/venue_bybit_eventshort.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import event_live as EL
BY = ROOT / "research_data/bybit_listings"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z="2026-09-30"):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025")]
stats = {"positions": 0, "covered": 0, "gross_hours": 0.0, "covered_gross_hours": 0.0, "funding_bp_per_day_binance": [], "funding_bp_per_day_bybit": []}


def bybit(base):
    for sym in (f"{base}USDT", f"1000{base}USDT"):
        f = BY / f"{sym}_1h.parquet"
        if f.exists():
            c = pd.read_parquet(f)["close"].astype(float); c.index = pd.DatetimeIndex(c.index).as_unit("ns")
            fu = pd.read_parquet(BY / f"{sym}_funding.parquet") if (BY / f"{sym}_funding.parquet").exists() else None
            fs = pd.Series(fu["last_funding_rate"].astype(float).to_numpy(), index=pd.DatetimeIndex(pd.to_datetime(fu["time"])).as_unit("ns").floor("h")) if fu is not None else pd.Series(dtype=float)
            k = 1000.0 if sym.startswith("1000") else 1.0
            return c / k, fs.groupby(level=0).sum()
    return None, None


def hook(P, CF):
    for n in P.columns:
        base = n[4:] if n.startswith("spo_") else n
        act = P[n][P[n] != 0]
        if act.empty:
            continue
        stats["positions"] += 1; g = float(act.abs().sum()); stats["gross_hours"] += g
        c, f = bybit(base)
        if c is None:
            continue
        need = act.index - pd.Timedelta(hours=1)
        if not need.isin(c.index).all():
            continue                                          # Bybit's 40-day file does not cover this position
        stats["covered"] += 1; stats["covered_gross_hours"] += g
        bc, bf = CF[n]
        win = (act.index.min(), act.index.max())
        stats["funding_bp_per_day_binance"].append(float(bf.loc[win[0]:win[1]].sum() / max((win[1] - win[0]).days, 1) * 1e4) if len(bf) else 0.0)
        stats["funding_bp_per_day_bybit"].append(float(f.loc[win[0]:win[1]].sum() / max((win[1] - win[0]).days, 1) * 1e4) if len(f) else 0.0)
        CF[n] = (c.combine_first(bc), f if len(f) else bf)          # Bybit where it exists, Binance outside the 40-day file (unused hours)
    return P


s0, _, _ = EL.pnl(idx); s1, _, _ = EL.pnl(idx, pre_cap=hook)
b0 = unit(CS.portfolio_v5(V7.assign(**{"listing short": s0}))[0]); b1 = unit(CS.portfolio_v5(V7.assign(**{"listing short": s1}))[0])
fb, fy = np.array(stats["funding_bp_per_day_binance"]), np.array(stats["funding_bp_per_day_bybit"])
out = {"event short positions": stats["positions"], "priced on Bybit": stats["covered"],
       "share of event-short gross on Bybit prices": round(stats["covered_gross_hours"] / stats["gross_hours"], 3),
       "funding paid by longs, bp a day (median over covered positions)": {"Binance": round(float(np.median(fb)), 2) if len(fb) else None, "Bybit": round(float(np.median(fy)), 2) if len(fy) else None},
       "event short (Binance prices)": per(s0), "event short (Bybit where covered)": per(s1), "corr of the two event shorts (daily)": round(float(dd(s0).corr(dd(s1))), 3),
       "book (Binance prices)": [shp(b0), per(b0)], "book (Bybit where covered)": [shp(b1), per(b1)]}
(ROOT / "results/v99/venue_bybit_eventshort.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
