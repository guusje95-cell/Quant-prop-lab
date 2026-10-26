"""Binance USDT-M bookDepth (public archive, data.binance.vision) -> hourly depth imbalance. Gen423.

    python -m qpl.lab.binance_depth BTCUSDT ETHUSDT ... [--first 2023-01-01 --last 2026-09-30]
Writes research_data/binance_depth/<SYM>_depth_1h.parquet: hourly means of bid / ask notional within 1, 2, 5 % and I1 / I2 / I5."""
from __future__ import annotations

import io
import sys
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research_data" / "binance_depth"
URL = "https://data.binance.vision/data/futures/um/daily/bookDepth/{s}/{s}-bookDepth-{d}.zip"


def one_day(sym: str, day: str):
    for _ in range(3):
        try:
            with urllib.request.urlopen(URL.format(s=sym, d=day), timeout=120) as r:
                raw = r.read()
            z = zipfile.ZipFile(io.BytesIO(raw)); d = pd.read_csv(z.open(z.namelist()[0]))
            break
        except Exception:                                        # noqa: BLE001 - missing day or network: retry, then skip
            d = None
    if d is None or d.empty:
        return None
    d["timestamp"] = pd.to_datetime(d["timestamp"]); d["h"] = d["timestamp"].dt.floor("h")
    p = d.pivot_table(index=["timestamp", "h"], columns="percentage", values="notional").reset_index()
    out = pd.DataFrame({"h": p["h"]})
    for k in (1, 2, 5):
        bid, ask = p.get(-k), p.get(k)
        if bid is None or ask is None:
            continue
        out[f"bid{k}"] = bid; out[f"ask{k}"] = ask; out[f"I{k}"] = (bid - ask) / (bid + ask)
    return out.groupby("h").mean()


def build(sym: str, first="2023-01-01", last="2026-09-30", workers=12):
    days = [f"{d:%Y-%m-%d}" for d in pd.date_range(first, last)]
    with ThreadPoolExecutor(workers) as ex:
        parts = [x for x in ex.map(lambda dd: one_day(sym, dd), days) if x is not None]
    df = pd.concat(parts).sort_index(); df = df[~df.index.duplicated()]
    OUT.mkdir(parents=True, exist_ok=True); df.to_parquet(OUT / f"{sym}_depth_1h.parquet")
    print(sym, len(df), df.index.min(), df.index.max(), f"{len(parts)}/{len(days)} days", flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]; kw = {}
    for flag in ("--first", "--last"):
        if flag in a:
            i = a.index(flag); kw[flag[2:]] = a[i + 1]; del a[i:i + 2]
    for s in a:
        build(s, **kw)
