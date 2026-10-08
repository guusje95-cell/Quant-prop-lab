"""Generation 6: H10 gold Asian-session drift (Topstep MGC) and H9 multi-asset daily TSMOM (FTMO swing)."""
from __future__ import annotations
import itertools, json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.data import loaders
from qpl.instruments import SPOT_COST_PRICE_UNITS, get
from qpl.research import pipeline as P, registry as R

ROOT = Path(__file__).resolve().parents[1]
SPL = {"train": P.SPLITS["train"], "validation": P.SPLITS["validation"]}


def h10():
    doc = {"family": "time-of-day/session", "hypothesis": "Gold drifts up during Asian hours (19:00-02:00 ET), excluding the 17:00-18:00 rollover artifact.",
           "rationale": "Asian physical/central-bank demand vs London-morning selling (documented intraday gold seasonality).",
           "falsification": "TRAIN net Sharpe <= 0.5 with MGC costs."}
    R.register_hypothesis("H10_GOLD_ASIA", doc["family"], 6, doc)
    ctx = P.context("dukascopy", "XAUUSD", "M15")
    days = P.trading_days(ctx); inst = get("MGC")
    rows = []
    for a, b in itertools.product([1140, 1200], [60, 120]):
        prm = dict(entry_min=a, exit_min=b, stop_atr=1.0)
        tr = P.backtest("overnight_drift", ctx, prm, inst)
        u = P.usd(tr, inst, contracts=1)
        sm = P.split_metrics(u, days, SPL)
        for s, m in sm.items():
            R.record(generation=6, family=doc["family"], hypothesis_id="H10_GOLD_ASIA", strategy="overnight_drift", instrument="MGC",
                     data_source="dukascopy:XAUUSD", timeframe="M15", params=prm, stage=f"screen_{s}", period=s, metrics=m,
                     decision="info", reason="gen6 screen")
        rows.append(dict(h="H10", prm=json.dumps(prm), tr_sh=sm["train"]["sharpe"], va_sh=sm["validation"]["sharpe"], n=sm["train"].get("trades")))
    return rows


def h9():
    doc = {"family": "trend/time-series momentum (daily)", "hypothesis": "12-month/6-month/3-month time-series momentum across FX majors, gold and equity-index CFDs earns a positive, diversified return.",
           "rationale": "Moskowitz, Ooi & Pedersen (2012); Hurst, Ooi & Pedersen (2017): under-reaction and de-leveraging flows.",
           "falsification": "TRAIN net Sharpe <= 0.5 after spread and financing costs.", "costs": "spread per SPOT_COST_PRICE_UNITS on turnover + ASSUMED financing drag 2%/yr of gross notional for index/gold CFDs, 1%/yr for FX."}
    R.register_hypothesis("H9_TSMOM", doc["family"], 6, doc)
    syms = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "XAUUSD", "US500", "US100", "DE40"]
    closes = {}
    for s in syms:
        d = loaders.load("dukascopy", s, "D1")["close"]
        d.index = d.index.tz_convert(None).normalize()
        closes[s] = d[d.index.dayofweek < 5]
    C = pd.DataFrame(closes).sort_index().ffill(limit=3)
    R_ = np.log(C).diff()
    rows = []
    for L in (63, 126, 252):
        sig = np.sign(R_.rolling(L, min_periods=L).sum())
        vol = R_.rolling(20, min_periods=15).std()
        w = (sig * (0.10 / np.sqrt(252)) / vol).clip(-5, 5)          # 10% ann vol per asset
        pos = w.shift(1)                                              # decided at close t-1, held over t
        cost = (w.diff().abs() * pd.DataFrame({s: SPOT_COST_PRICE_UNITS[s] / C[s] for s in syms})).shift(1)
        fin = pos.abs() * pd.Series({s: (0.01 if len(s) == 6 and s not in ("XAUUSD",) else 0.02) for s in syms}) / 252
        port = (pos * R_ - cost.fillna(0) - fin.fillna(0)).mean(1, skipna=True)
        for sname, (a, b) in SPL.items():
            x = port.loc[a:b].dropna()
            sh = float(x.mean() / x.std() * np.sqrt(252))
            R.record(generation=6, family=doc["family"], hypothesis_id="H9_TSMOM", strategy="tsmom_daily", instrument="10 CFDs/FX",
                     data_source="dukascopy:D1", timeframe="D1", params={"lookback": L, "vol_target_asset": 0.10}, stage=f"screen_{sname}",
                     period=sname, metrics={"sharpe": sh, "ann_ret": float(x.mean() * 252), "days": len(x)}, decision="info", reason="gen6 screen")
        rows.append(dict(h="H9", prm=f"L={L}", tr_sh=float(port.loc[SPL['train'][0]:SPL['train'][1]].pipe(lambda z: z.mean()/z.std()*np.sqrt(252))),
                         va_sh=float(port.loc[SPL['validation'][0]:SPL['validation'][1]].pipe(lambda z: z.mean()/z.std()*np.sqrt(252))), n=np.nan))
    return rows


if __name__ == "__main__":
    df = pd.DataFrame(h10() + h9())
    df.to_csv(ROOT / "results" / "gen6_misc.csv", index=False)
    print(df.round(3).to_string())
