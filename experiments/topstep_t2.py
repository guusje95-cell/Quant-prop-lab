"""Gen24 T2: daily trend held 17:00 CT -> 15:00 CT (Topstep trading day). Protocol config/topstep_t2_protocol.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.research import factory as F, v6  # noqa: E402
from qpl.statistics import tests as T  # noqa: E402
from qpl.strategies import futures_factors as FF  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROTO = "config/topstep_t2_protocol.json"
PR = json.loads((ROOT / PROTO).read_text())
COST = PR["costs_round_trip_bp_of_notional"]
PER = PR["periods"]


def sessions(h: pd.DataFrame) -> pd.DataFrame:
    """Topstep trading day D: bars from 18:00 ET on the previous evening through the 15:00 ET bar of D (exit = its close)."""
    e = h.copy(); e.index = h.index.tz_convert("America/New_York")
    e["key"] = (e.index + pd.Timedelta(hours=6)).normalize().tz_localize(None)    # 18:00 ET -> next date
    e["hr"] = e.index.hour
    w = e[(e.hr >= 18) | (e.hr <= 15)]
    g = w.groupby("key")
    first_hr = g.hr.first(); last_hr = g.hr.last()
    s = pd.DataFrame({"o": g.open.first().where(first_hr == 18), "c": g.close.last().where(last_hr == 15), "hi": g.high.max(), "lo": g.low.min()}).dropna()
    s = s[s.index.dayofweek < 5]
    s["sess_ret"] = s.c / s.o - 1
    s["on_ret"] = s.o / s.c.shift(1) - 1
    s["mae_long"] = s.lo / s.o - 1; s["mae_short"] = 1 - s.hi / s.o
    return s


def t1(s: pd.DataFrame, cost_bp: float, cmult: float = 1.0) -> pd.DataFrame:
    r_close = np.log(s.c).diff().to_frame("x")
    fc = FF.ewmac(r_close, ((8, 32), (16, 64), (32, 128)))["x"] * 2      # ewmac returns forecast/2 capped +-1 -> back to [-2,2]
    fc = fc.clip(-1, 1).shift(1)                                         # decided with closes through the previous day
    vol = s.sess_ret.rolling(20, min_periods=15).std().shift(1)
    pos = (fc / vol).replace([np.inf, -np.inf], np.nan)
    pos = pos / pos.abs().rolling(250, min_periods=60).mean().shift(1)   # normalise to ~1 unit of risk on average (causal)
    gross = pos * s.sess_ret * (1 / vol.where(vol > 0)) * vol           # = pos * sess_ret
    gross = pos * s.sess_ret
    cost = pos.abs() * cost_bp * cmult / 1e4
    worst = np.where(pos > 0, pos * s.mae_long, -pos * s.mae_short * -1) if False else np.minimum(0, np.where(pos > 0, pos * s.mae_long, (-pos) * s.mae_short))
    d = pd.DataFrame({"pos": pos, "gross": gross, "net": gross - cost, "cost": cost, "worst": worst, "sess_ret": s.sess_ret, "on_ret": s.on_ret,
                      "fc": fc}).dropna(subset=["pos"])
    d["dc_gross"] = d.pos * (d.sess_ret + d.on_ret.shift(-1).fillna(0) * 0)     # placeholder (diagnostic computed separately)
    return d


def load(src, sym):
    p = ROOT / (f"data/processed/dukascopy/{sym}_H1.parquet" if src == "duka" else f"data/processed/topstepx/{sym}_1h.parquet")
    return pd.read_parquet(p)[["open", "high", "low", "close"]]


def pooled(books: dict, a, z, col="net"):
    X = pd.DataFrame({k: v.loc[a:z, col] for k, v in books.items()}).fillna(0)
    tot = X.sum(axis=1)
    yrs = (tot.index[-1] - tot.index[0]).days / 365.25
    ann = len(tot) / yrs
    sh = float(tot.mean() / tot.std() * np.sqrt(ann)) if tot.std() > 0 else 0.0
    return sh, tot, X


def stats(books, a, z):
    sh, tot, X = pooled(books, a, z)
    shg, _, _ = pooled(books, a, z, "gross")
    days = int((pd.DataFrame({k: v.loc[a:z, "pos"] for k, v in books.items()}).abs() > 0).sum().sum())
    pos_days = X.stack(); pos_days = pos_days[pos_days != 0]
    gp, gl = pos_days[pos_days > 0].sum(), -pos_days[pos_days < 0].sum()
    eq = tot.cumsum()
    return {"net_sharpe": round(sh, 3), "gross_sharpe": round(shg, 3), "instrument_days": days, "win_rate": round(float((pos_days > 0).mean()), 3),
            "profit_factor": round(float(gp / gl), 3) if gl > 0 else None, "max_dd_units": round(float((eq - eq.cummax()).min()), 2),
            "share_inst_positive": round(float((X.mean() > 0).mean()), 3), "per_inst_sharpe": {k: round(float(X[k].mean() / X[k].std() * np.sqrt(252)), 2) if X[k].std() > 0 else 0 for k in X},
            "nw_p": round(T.newey_west_t(tot.to_numpy(), lags=5)[1], 4), "by_year_units": {int(y): round(float(v), 2) for y, v in tot.groupby(tot.index.year).sum().items()}}


out = {}
dmap = PR["instruments"]["dev_proxies (Dukascopy H1)"]
S = {sym: sessions(load("duka", sym)) for sym in dmap}
B = {sym: t1(S[sym], COST[fut]) for sym, fut in dmap.items()}
B2 = {sym: t1(S[sym], COST[fut], 2.0) for sym, fut in dmap.items()}
B3 = {sym: t1(S[sym], COST[fut], 3.0) for sym, fut in dmap.items()}
# diagnostic: daily-trend P&L split session vs overnight (same position held close-to-close)
diag = {}
for sym, b in B.items():
    s = S[sym]; p = b.pos
    on_next = s.on_ret.reindex(p.index)                       # overnight INTO day D (before the session) earned by a position decided at D-1 close
    diag[sym] = {"session_gross_sum": round(float((p * s.sess_ret.reindex(p.index)).sum()), 2), "overnight_gross_sum": round(float((p * on_next).sum()), 2)}
out["diagnostic_session_vs_overnight"] = diag
F.Hypothesis("T2_TREND_GLOBEX", "prop/topstep-intraday-trend", PR["hypothesis"], "trend premium accrual during the day session",
             json.dumps(PR["gates"]), "Dukascopy H1 + TopstepX 1h", "single spec", "zero", PROTO, generation=24).register()
res = {"DEV": stats(B, *PER["DEV"]), "DEV_2x": pooled(B2, *PER["DEV"])[0], "DEV_3x": pooled(B3, *PER["DEV"])[0]}
d = res["DEV"]
res["dev_pass"] = bool(d["net_sharpe"] >= 0.5 and d["share_inst_positive"] >= 0.6)
v6.record("T2_TREND_GLOBEX", "prop/topstep", "T1", {}, "DEV", d, 24, PROTO, "Dukascopy H1")
if res["dev_pass"]:
    res["VAL"] = stats(B, *PER["VAL"]); res["val_pass"] = res["VAL"]["net_sharpe"] >= 0.3
    v6.record("T2_TREND_GLOBEX", "prop/topstep", "T1", {}, "VAL", res["VAL"], 24, PROTO, "Dukascopy H1")
    if res["val_pass"]:
        res["TEST"] = stats(B, *PER["TEST"]); res["TEST_2x"] = pooled(B2, *PER["TEST"])[0]; res["TEST_3x"] = pooled(B3, *PER["TEST"])[0]
        res["test_pass"] = bool(res["TEST"]["net_sharpe"] > 0 and res["TEST_2x"] >= 0)
        v6.record("T2_TREND_GLOBEX", "prop/topstep", "T1", {}, "TEST_LOOK", res["TEST"], 24, PROTO, "Dukascopy H1")
        if res["test_pass"]:
            SF = {f: sessions(load("tsx", f)) for f in PR["instruments"]["fresh (TopstepX 1h, real CME)"]}
            BF = {f: t1(SF[f], COST[f]) for f in SF}
            start = max(b.index[0] for b in BF.values())
            res["FRESH"] = stats(BF, str(start.date()), PER["FRESH"][1])
            res["fresh_pass"] = bool(pooled(BF, str(start.date()), PER["FRESH"][1])[1].mean() > 0)
            v6.record("T2_TREND_GLOBEX", "prop/topstep", "T1", {}, "FRESH_LOOK", res["FRESH"], 24, PROTO, "TopstepX")
v = "REJECTED" if not res["dev_pass"] else ("EXPLORATORY" if not res.get("val_pass") else
     ("PROMISING_BUT_UNVALIDATED" if res.get("test_pass") and res.get("fresh_pass") else "EXPLORATORY"))
res["verdict"] = v
F.decide(F.Hypothesis("T2_TREND_GLOBEX", "", "", "", "", "", "", "", PROTO, generation=24), v,
         json.dumps({k: res[k]["net_sharpe"] for k in ("DEV", "VAL", "TEST", "FRESH") if k in res}), {"protocol": PROTO})
out["T2"] = res
(ROOT / "results/topstep_t2.json").write_text(json.dumps(out, indent=1, default=str))
print(json.dumps(out, indent=1, default=str)[:6000])
