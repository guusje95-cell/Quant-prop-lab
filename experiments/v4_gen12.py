"""V4 generation 12: ETH/BTC relative value (R1 reversion, R2 momentum) + 4h trend variant (C11). Protocol: config/gen12_protocol.json."""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import vector as VB  # noqa: E402
from qpl.data import crypto as CD  # noqa: E402
from qpl.research import crypto_factory as CF, factory as F, registry as R  # noqa: E402
from qpl.strategies import crypto as CS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROTO = "config/gen12_protocol.json"
OUT = {}


def rec_(hyp, label, params, stage, m):
    rid = R.record(generation=12, family=hyp.family, hypothesis_id=hyp.id, strategy=label, instrument="ETH/BTC" if "R" in hyp.id[:1] else "BTCUSD",
                   data_source="see protocol", timeframe="1D", params=params, stage=stage, period=stage, train_period="", validation_period="",
                   oos_period="", metrics=m, decision="info", reason="v4 gen12")
    F.append({"kind": "experiment", "registry_id": rid, "hypothesis_id": hyp.id, "asset_class": "crypto", "signal": label, "params": params,
              "stage": stage, "protocol": PROTO, "summary": {k: m.get(k) for k in ("sharpe", "max_dd")}})


def pair_signal(lr: pd.Series, kind: str) -> pd.Series:
    """+1 = long ETH / short BTC. Decided at close t."""
    if kind == "rev":
        z = (lr - lr.rolling(20).mean()) / lr.rolling(20).std()
        trig = pd.Series(np.where(z > 1.5, -1.0, np.where(z < -1.5, 1.0, 0.0)), index=lr.index)
        return CS.hold_for(trig, 5)
    return np.sign(lr.diff(60)).fillna(0.0)


def pair_pnl(eth: pd.DataFrame, btc: pd.DataFrame, s: pd.Series, f_eth, f_btc, lag=0) -> pd.Series:
    s = s.shift(lag).fillna(0.0)
    a = VB.daily(VB.run(eth, 0.5 * s, 7.0, f_eth))["net"]
    b = VB.daily(VB.run(btc, -0.5 * s.reindex(btc.index).fillna(0.0), 7.0, f_btc))["net"]
    return a.add(b, fill_value=0.0)


raw = pd.read_csv(ROOT / "data/raw/dukascopy/crypto/ethusdt/ETHUSDT_D1.csv", sep="\t")
raw.columns = [c.lower() for c in raw.columns]
eth = raw.set_index(pd.to_datetime(raw["time"], utc=True))[["open", "high", "low", "close"]].astype(float).sort_index()
btc = CD.btc_bars("1D").reindex(eth.index).dropna(subset=["close"])
eth = eth.loc[btc.index]
fund_btc, _ = CF.btc_funding()
grid = pd.date_range("2017-08-01", "2023-09-12", freq="8h", tz="UTC")
fund_eth = pd.Series(0.0001, index=grid); fe = CD.funding_binance_2020_2024("ETH")
c = fund_eth.index.intersection(fe.index); fund_eth.loc[c] = fe.loc[c].to_numpy()
lr = np.log(eth["close"] / btc["close"])

rec = CD.funding_recent("binance"); rec["ts"] = rec.settlement_ts.dt.floor("h")
def perp(sym):
    g = rec[rec.venue_symbol == sym].drop_duplicates("ts").set_index("ts").sort_index()
    m = g["mark_price"].astype(float); m = m[m.index.hour == 0]
    return pd.DataFrame({"open": m, "high": m, "low": m, "close": m}), g["rate_raw"].astype(float)
pe, pfe = perp("ETHUSDT"); pb, pfb = perp("BTCUSDT")
plr = np.log(pe["close"] / pb["close"])

for hid, kind, st in (("R1_ETHBTC_REVERSION", "rev", "ETH/BTC ratio deviations revert"), ("R2_ETHBTC_MOMENTUM", "mom", "ETH/BTC relative momentum persists")):
    hyp = F.Hypothesis(hid, "crypto/relative value", st, "Rotation flows between the two largest coins; arbitrage capital limits (R1) or slow diffusion (R2).",
                       "see protocol", "BTC+ETH daily", "single rule", "zero (dollar-neutral)", PROTO, generation=12)
    hyp.register()
    d = pair_pnl(eth, btc, pair_signal(lr, kind), fund_eth, fund_btc)
    o = {"train": VB.stats(d.loc["2018-03-01":"2020-12-31"]), "oos": None, "holdout": None}
    rec_(hyp, kind, {}, "gen12_train", o["train"])
    o["train_pass"] = o["train"]["sharpe"] >= 0.5
    if o["train_pass"]:
        o["oos"] = VB.stats(d.loc["2021-01-01":"2023-09-09"]); rec_(hyp, kind, {}, "gen12_OOS_LOOK", o["oos"])
        o["oos_pass"] = o["oos"]["sharpe"] > 0.3
        if o["oos_pass"]:
            dh = pair_pnl(pe, pb, pair_signal(plr, kind), pfe, pfb, lag=1)
            o["holdout"] = VB.stats(dh.loc["2025-11-01":"2026-09-20"]); rec_(hyp, kind, {}, "gen12_HOLDOUT_LOOK", o["holdout"])
            o["holdout_pass"] = o["holdout"]["sharpe"] > 0
    v = "REJECT" if not o["train_pass"] else "EXPLORATORY" if not o.get("oos_pass") else ("VALIDATION_CANDIDATE" if not o.get("holdout_pass") else "PAPER_TRADING_CANDIDATE")
    if v == "PAPER_TRADING_CANDIDATE":
        v = "VALIDATION_CANDIDATE"   # mirror ETH provenance + 10-month holdout: capped one level below until longer clean data exists
    F.decide(hyp, v, json.dumps({k: (round(x["sharpe"], 2) if isinstance(x, dict) else x) for k, x in o.items()}), {"protocol": PROTO})
    o["verdict"] = v; OUT[hid] = o

# C11 4h trend variant (diversification analysis)
hyp = F.Hypothesis("C11_TSMOM_4H", "crypto/trend", "BTC trend on 4h bars (variant of C1)", "as C1", "see protocol", "Bitstamp 4h",
                   "lookback {30,90,180} bars", "buy&hold-VT", PROTO, generation=12)
hyp.register()
b4 = CD.btc_bars("4h").loc["2014-06-01":]
ct1 = VB.daily(VB.run(CD.btc_bars("1D").loc["2014-06-01":], CS.trend_ensemble(CD.btc_bars("1D").loc["2014-06-01":], {}), 7.0, fund_btc))["net"]
OUT["C11_TSMOM_4H"] = {}
for L in (30, 90, 180):
    r = CF.evaluate(hyp, "tsmom", {"lookback": L, "vol_lb": 180}, rule="4h", stage="gen12_C11")
    d = VB.daily(VB.run(b4, CS.tsmom(b4, {"lookback": L, "vol_lb": 180}), 7.0, fund_btc))["net"]
    t, v = r["periods"]["train"], r["periods"]["validation"]
    OUT["C11_TSMOM_4H"][L] = {"train": t["sharpe"], "train_resid": t.get("residual_sharpe"), "val": v["sharpe"], "val_resid": v.get("residual_sharpe"),
                               "corr_with_CT1_2015_21": float(d.loc["2015":"2021"].corr(ct1.loc["2015":"2021"]))}
F.decide(hyp, "EXPLORATORY", "trend variant; correlation with CT1 reported; not advanced (same family, no new information)", {"protocol": PROTO,
         "res": OUT["C11_TSMOM_4H"]})
(ROOT / "results/v4_gen12.json").write_text(json.dumps(OUT, indent=1, default=float))
print(json.dumps(OUT, indent=1, default=float))
