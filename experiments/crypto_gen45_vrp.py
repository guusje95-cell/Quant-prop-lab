"""Gen45 (config/crypto_gen45_protocol.json): monthly short 30d variance proxy on BTC/ETH using Deribit DVOL."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qpl.data import static_klines as SK  # noqa: E402
from qpl.research import factory as F  # noqa: E402

PROTO = "config/crypto_gen45_protocol.json"
RAW = ROOT / "data/raw/deribit"


def dvol(cur):
    p = RAW / f"{cur}_DVOL.parquet"
    if p.exists():
        return pd.read_parquet(p)["close"]
    rows = []; a = int(pd.Timestamp("2021-01-01").timestamp() * 1000); now = int(time.time() * 1000)
    while a < now:
        b = min(a + 300 * 86400000, now)
        r = requests.get("https://www.deribit.com/api/v2/public/get_volatility_index_data",
                         params={"currency": cur, "start_timestamp": a, "end_timestamp": b, "resolution": "1D"}, timeout=30).json()
        rows += r["result"]["data"]; a = b; time.sleep(0.3)
    df = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close"]).drop_duplicates("t")
    df.index = pd.DatetimeIndex(pd.to_datetime(df.pop("t"), unit="ms")).normalize(); df = df.sort_index()
    df.to_parquet(p); return df["close"]


C = SK.load("1d")["close"]
res = {}
for cur in ("BTC", "ETH"):
    iv = dvol(cur) / 100
    lr = np.log(C[cur]).diff()
    months = pd.date_range("2021-04-01", "2026-09-01", freq="MS")
    rows = []
    for m in months:
        if m not in iv.index:
            continue
        ive = iv.loc[m] - 0.015
        rv = lr.loc[m + pd.Timedelta(days=1): m + pd.Timedelta(days=30)].std() * np.sqrt(365)
        pnl = 0.005 * 100 * (ive ** 2 - rv ** 2) / (2 * ive)          # vega budget 0.5% of capital per vol point
        rows.append((m, ive, rv, pnl))
    res[cur] = pd.DataFrame(rows, columns=["month", "iv_eff", "rv", "pnl"]).set_index("month")
book = (res["BTC"]["pnl"] + res["ETH"]["pnl"]) / 2


def st(x):
    return {"n": int(len(x)), "mean_month": round(float(x.mean()), 4), "pos_months": round(float((x > 0).mean()), 3),
            "sharpe_ann": round(float(x.mean() / x.std() * np.sqrt(12)), 2), "worst_month": round(float(x.min()), 4),
            "worst_3": [round(float(v), 4) for v in x.nsmallest(3)], "total": round(float(x.sum()), 4)}


out = {"ALL": st(book), "DEVVAL": st(book.loc[:"2023-12"]), "TEST": st(book.loc["2024-01":]),
       "by_year": {int(y): round(float(g.sum()), 4) for y, g in book.groupby(book.index.year)},
       "mean_iv_minus_rv_volpts": {c: round(float((res[c]["iv_eff"] - res[c]["rv"]).mean() * 100), 2) for c in res}}
t = out["TEST"]
out["STEADY_VRP"] = bool(t["pos_months"] >= 0.70 and t["sharpe_ann"] >= 1.0 and t["worst_month"] > -3 * t["mean_month"] and out["ALL"]["mean_month"] > 0)
F.append({"kind": "holdout_evaluation", "hypothesis_id": "GEN45_VRP_PROXY", "protocol": PROTO, "result": {"TEST": t, "STEADY": out["STEADY_VRP"]}})
(ROOT / "results/crypto_gen45_vrp.json").write_text(json.dumps(out, indent=1, default=float))
print(json.dumps(out, indent=1, default=float))
