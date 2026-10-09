"""Single-use cross-asset confirmation of the frozen CT1 rule (config/ct1_crossasset_protocol.json)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import vector as VB  # noqa: E402
from qpl.data import crypto as CD, loaders  # noqa: E402
from qpl.research import factory as F  # noqa: E402
from qpl.strategies import crypto as CS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
COST = 7.0
out = {}


def resid_sharpe(x, y):
    beta = np.cov(x, y)[0, 1] / y.var() if y.var() > 0 else 0.0
    return float(VB.stats(x - beta * y)["sharpe"]), float(beta)


# ---------------- Test A: ETH (mirror ETHUSDT daily)
raw = pd.read_csv(ROOT / "data/raw/dukascopy/crypto/ethusdt/ETHUSDT_D1.csv", sep="\t")
raw.columns = [c.lower() for c in raw.columns]
raw["time"] = pd.to_datetime(raw["time"], utc=True)
eth = raw.set_index("time")[["open", "high", "low", "close", "volume"]].astype(float).sort_index()
fe = CD.funding_binance_2020_2024("ETH")
grid = pd.date_range("2017-08-01", "2023-09-12", freq="8h", tz="UTC")
fund = pd.Series(0.0001, index=grid)
c = fund.index.intersection(fe.index); fund.loc[c] = fe.loc[c].to_numpy()
d = VB.daily(VB.run(eth, CS.trend_ensemble(eth, {}), COST, fund))["net"].loc["2018-01-01":"2023-09-10"]
bh = VB.daily(VB.run(eth, CS.buy_hold_vt(eth, {}), COST, fund))["net"].loc["2018-01-01":"2023-09-10"]
rs, beta = resid_sharpe(d, bh)
out["A_ETH"] = {**VB.stats(d), "residual_sharpe": rs, "beta": beta, "buyhold_vt_sharpe": VB.stats(bh)["sharpe"],
                "by_year": {int(k): round(float(v), 3) for k, v in d.groupby(d.index.year).sum().items()},
                "pass": bool(VB.stats(d)["sharpe"] > 0.3 and rs > 0)}

# ---------------- Test B: 22 Binance USDT perps, mark prices at 00:00 UTC, 2025-08..2026-09
fr = CD.funding_recent("binance")
fr = fr[fr.venue_symbol.str.endswith("USDT")].copy()
fr["ts"] = fr.settlement_ts.dt.floor("h")
nets, bhs, per = {}, {}, {}
for sym, g in fr.groupby("venue_symbol"):
    g = g.drop_duplicates("ts").set_index("ts").sort_index()
    mk = g["mark_price"].astype(float)
    daily_mark = mk[mk.index.hour == 0]
    if len(daily_mark) < 200:
        continue
    bars = pd.DataFrame({"open": daily_mark, "high": daily_mark, "low": daily_mark, "close": daily_mark})
    w = CS.trend_ensemble(bars, {}).shift(1).fillna(0.0)            # pre-registered extra 1-day lag
    f = g["rate_raw"].astype(float)
    n = VB.daily(VB.run(bars, w, COST, f))["net"]
    b = VB.daily(VB.run(bars, CS.buy_hold_vt(bars, {}).shift(1).fillna(0), COST, f))["net"]
    nets[sym], bhs[sym] = n, b
    per[sym] = round(VB.stats(n.loc["2025-10-01":])["sharpe"], 2)
N, B = pd.DataFrame(nets).fillna(0), pd.DataFrame(bhs).fillna(0)
port, bport = N.mean(axis=1), B.mean(axis=1)
# warm-up: 120-day lookback needs history -> evaluate from the first date at which every component is defined
warm = port.index[0] + pd.Timedelta(days=125)
p_eval, b_eval = port.loc[warm:], bport.loc[warm:]
rs, beta = resid_sharpe(p_eval, b_eval)
out["B_PERPS"] = {"n_symbols": N.shape[1], "eval_start": str(warm.date()), **VB.stats(p_eval), "residual_sharpe": rs, "beta": beta,
                  "buyhold_vt_sharpe": VB.stats(b_eval)["sharpe"], "per_symbol_sharpe_full": per,
                  "share_symbols_positive": float(np.mean([v > 0 for v in per.values()])),
                  "pass": bool(VB.stats(p_eval)["sharpe"] > 0 and rs > 0),
                  "note": "warm-up truncation: TSMOM-120 needs 120 days; evaluation window is therefore ~8 months"}
(ROOT / "results" / "v4_ct1_crossasset.json").write_text(json.dumps(out, indent=1, default=float))
F.append({"kind": "holdout_evaluation", "hypothesis_id": "CT1_TREND_ENSEMBLE", "protocol": "config/ct1_crossasset_protocol.json",
          "result": {k: {kk: v.get(kk) for kk in ("sharpe", "residual_sharpe", "max_dd", "pass")} for k, v in out.items()}})
print(json.dumps(out, indent=1, default=float))
