"""Gen44 (config/crypto_gen44_protocol.json): BTC/ETH funding carry (long spot / short perp) on Deribit funding history."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qpl.data import deribit as DB  # noqa: E402
from qpl.research import factory as F  # noqa: E402

PROTO = "config/crypto_gen44_protocol.json"
PER = {"DEV": ("2019-05-01", "2021-12-31"), "VAL": ("2022-01-01", "2023-12-31"), "TEST": ("2024-01-01", "2026-10-13")}
SQ = np.sqrt(365)


def carry(inst, cmult=1.0, noise=0.0, seed=0):
    f = DB.load(inst)
    h = f["interest_1h"].astype(float)
    ann7 = f["interest_8h"].astype(float).rolling(24 * 7, min_periods=24 * 5).mean() * 3 * 365
    state = np.zeros(len(h)); cur = 0.0; a = ann7.to_numpy()
    for i in range(len(h)):
        if cur == 0 and a[i] > 0.05:
            cur = 1.0
        elif cur == 1 and a[i] < 0:
            cur = 0.0
        state[i] = cur
    pos = pd.Series(state, index=h.index).shift(1).fillna(0)          # decided on information through the previous hour
    pnl = pos * h - pos.diff().abs().fillna(0) * 0.0015 * cmult       # 30 bp per round trip = 15 bp per switch
    daily = pnl.resample("D").sum()
    if noise:
        daily = daily + pd.Series(np.random.default_rng(seed).normal(0, noise, len(daily)), index=daily.index) * (pos.resample("D").max() > 0)
    return daily / 1.25, pos.resample("D").mean()                      # return on capital


def stats(x):
    x = x.dropna(); m = (1 + x).resample("ME").prod() - 1; eq = (1 + x).cumprod()
    return {"sharpe": round(float(x.mean() / x.std() * SQ), 2) if x.std() > 0 else None,
            "cagr": round(float(eq.iloc[-1] ** (365 / len(x)) - 1), 4), "pos_months": round(float((m > 0).mean()), 3),
            "worst_month": round(float(m.min()), 4), "max_dd": round(float((eq / eq.cummax() - 1).min()), 4)}


out = {}
legs = {c: carry(f"{c}-PERPETUAL") for c in ("BTC", "ETH")}
book = (legs["BTC"][0] + legs["ETH"][0]) / 2
stress = (carry("BTC-PERPETUAL", 2.0, 0.001, 1)[0] + carry("ETH-PERPETUAL", 2.0, 0.001, 2)[0]) / 2
out["time_in_position"] = {c: round(float(legs[c][1].mean()), 3) for c in legs}
out["CARRY"] = {p: stats(book.loc[a:z]) for p, (a, z) in PER.items()}
out["CARRY"]["ALL"] = stats(book)
out["CARRY_stress"] = {p: stats(stress.loc[a:z]) for p, (a, z) in PER.items()}
out["CARRY"]["by_year_return"] = {int(y): round(float((1 + g).prod() - 1), 4) for y, g in book.groupby(book.index.year)}
t, ts = out["CARRY"]["TEST"], out["CARRY_stress"]["TEST"]
out["STEADY_CARRY"] = bool(t["pos_months"] >= 0.75 and (t["sharpe"] or 0) >= 2.0 and t["cagr"] >= 0.04 and (ts["sharpe"] or 0) >= 1.0)
# combination with C* (calendar daily, equal capital)
C = pd.read_pickle(ROOT / "results/crypto_gen38_Cstar_series.pkl")["net"]
cal = pd.date_range("2019-05-01", "2026-10-08")
combo = 0.5 * C.reindex(cal).fillna(0) + 0.5 * book.reindex(cal).fillna(0)
out["Cstar_alone_2019_2026"] = stats(C.reindex(cal).fillna(0)); out["COMBO_50_50"] = stats(combo)
out["COMBO_by_period"] = {p: stats(combo.loc[a:z]) for p, (a, z) in PER.items()}
F.append({"kind": "holdout_evaluation", "hypothesis_id": "GEN44_FUNDING_CARRY", "protocol": PROTO, "result": {"TEST": t, "STEADY": out["STEADY_CARRY"]}})
(ROOT / "results/crypto_gen44_carry.json").write_text(json.dumps(out, indent=1, default=float))
print(json.dumps(out, indent=1, default=float))
