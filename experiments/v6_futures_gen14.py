"""V6 gen14: implementation research on futures survivors (buffering, leverage caps, integer contracts at real capital).
Protocol config/v6_gen14_protocol.json. Signals unchanged; decisions on DISCOVERY+VALIDATION only."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import panel as PB  # noqa: E402
from qpl.data import futures_panel as FP  # noqa: E402
from qpl.research import factory as F, v6  # noqa: E402
from qpl.strategies import futures_factors as FF  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROTO = "config/v6_gen14_protocol.json"
PER = v6.protocol("v6_futures_protocol.json")["periods"]
P = FP.build(); U, utab = FP.universe(P)
ret, cost, cy = P["ret"][U], P["cost"][U], P["carry"][U]
SIG = PB.sigma(ret)
combo = (FF.ct1_transfer(ret).fillna(0) + FF.tsmom(ret).fillna(0) + FF.ewmac(ret).fillna(0) + FF.carry(ret, cy, 21).fillna(0)) / 4
combo = combo.where(ret.notna().cumsum() > 0)
SIGNALS = {"F7_COMBO": combo, "F2_EWMAC": FF.ewmac(ret)}
STAGES = ("DISCOVERY", "VALIDATION", "TEST", "HOLDOUT")


def pnl_from_weights(W: pd.DataFrame, cm=1.0, lag=2) -> pd.DataFrame:
    r0 = ret.fillna(0.0)
    gross = (W.shift(lag) * r0).sum(axis=1)
    turn = (W.shift(lag - 1) - W.shift(lag)).abs()
    cst = (turn * cost.reindex_like(W).ffill().shift(lag - 1)).sum(axis=1) * cm
    return pd.DataFrame({"gross": gross, "cost": cst, "net": gross - cst, "turnover": turn.sum(axis=1), "gross_lev": W.abs().sum(axis=1), "n": 0})


def buffer(W: pd.DataFrame, b: float) -> pd.DataFrame:
    m = W.abs().rolling(252, min_periods=20).mean().fillna(W.abs()).to_numpy()
    w = W.to_numpy(); out = np.zeros_like(w); held = np.zeros(w.shape[1])
    for t in range(len(w)):
        lo, hi = held - b * m[t], held + b * m[t]
        tgt = w[t]
        held = np.where(tgt < lo, tgt + b * m[t], np.where(tgt > hi, tgt - b * m[t], held))
        held = np.where(tgt == 0, 0.0, held)
        out[t] = held
    return pd.DataFrame(out, index=W.index, columns=W.columns)


def sh(d, st):
    return round(PB.stats(d["net"].loc[PER[st][0]:PER[st][1]])["sharpe"], 3)


out = {"G14a": {}, "G14b": {}, "G14c": {}}
RUN_A = "--only-c" not in sys.argv
for name, s in (SIGNALS.items() if RUN_A else []):
    _, W = PB.run(ret, s, cost, sig=SIG, return_weights=True)
    base = {cm: pnl_from_weights(W, cm) for cm in (1, 3)}
    rows = {"b0": {f"{st}_{cm}x": sh(base[cm], st) for st in STAGES for cm in (1, 3)} | {"turnover_val": float(base[1]["turnover"].loc["2005":"2013"].mean() * 256)}}
    for b in (0.05, 0.10, 0.20, 0.40):
        Wb = buffer(W, b)
        d = {cm: pnl_from_weights(Wb, cm) for cm in (1, 3)}
        rows[f"b{b}"] = {f"{st}_{cm}x": sh(d[cm], st) for st in STAGES for cm in (1, 3)} | {"turnover_val": float(d[1]["turnover"].loc["2005":"2013"].mean() * 256)}
    ok = [b for b in (0.05, 0.10, 0.20, 0.40)
          if all(rows[f"b{b}"][f"{st}_3x"] - rows["b0"][f"{st}_3x"] >= 0.10 and rows["b0"][f"{st}_1x"] - rows[f"b{b}"][f"{st}_1x"] <= 0.05 for st in ("DISCOVERY", "VALIDATION"))]
    rows["adopted_b"] = ok[0] if ok else None
    out["G14a"][name] = rows
    v6.record(f"G14_BUFFER_{name}", "futures/implementation", "buffer_grid", {"grid": [0.05, 0.1, 0.2, 0.4]}, "DISCOVERY+VALIDATION", {"rows": rows}, 14, PROTO, "futures panel")
    # G14b leverage caps (on the adopted or unbuffered weights)
    Wx = buffer(W, ok[0]) if ok else W
    for L in (4, 6, 8):
        lev = Wx.abs().sum(axis=1)
        Wl = Wx.mul((L / lev).clip(upper=1.0).fillna(1.0), axis=0)
        d = pnl_from_weights(Wl)
        out["G14b"].setdefault(name, {})[f"L{L}"] = {st: sh(d, st) for st in STAGES} | {"share_days_capped": float((lev > L).loc["2005":].mean())}
    print(name, json.dumps(rows), json.dumps(out["G14b"][name]))

# ---------------- G14c integer contracts at real capital
cfg = FP.meta()
fxdir = FP.SRC / "fx_prices_csv"
fx = {}
for cur in cfg.Currency.unique():
    if cur == "USD":
        continue
    p = fxdir / f"{cur}USD.csv"
    if p.exists():
        s = pd.read_csv(p, parse_dates=["DATETIME"]).set_index("DATETIME")["PRICE"]
        s.index = s.index.normalize(); fx[cur] = s[~s.index.duplicated(keep="last")]
_, dropped = FP.dedupe(P)
members = {k: [k] + [d for d, kk in dropped.items() if kk == k] for k in U}
pr_all, ret_all, cost_all = P["price"], P["ret"], P["cost"]
qual = FP.quality(P)
choice = {}
for k, mem in members.items():
    best, best_n = k, np.inf
    for m in mem:
        if m not in cfg.index:
            continue
        cur = cfg.loc[m, "Currency"]
        f = fx[cur].reindex(pr_all.index).ffill() if cur in fx else (1.0 if cur == "USD" else np.nan)
        notional = (pr_all[m].abs() * cfg.loc[m, "Pointsize"] * f).loc["2015":"2024"].median()
        cvol = qual.loc[m, "median_cost_bp"] / 1e4 / qual.loc[m, "ann_vol"]
        if np.isfinite(notional) and notional < best_n and cvol <= 0.02:
            best, best_n = m, notional
    choice[k] = best
U2 = [choice[k] for k in U]
ret2, cost2 = ret_all[U2], cost_all[U2]
notional = pd.DataFrame({m: pr_all[m].abs() * cfg.loc[m, "Pointsize"] * (fx[cfg.loc[m, "Currency"]].reindex(pr_all.index).ffill() if cfg.loc[m, "Currency"] in fx else 1.0) for m in U2})
notional = notional.ffill()   # audit V6-B1b: exchange holidays left NaN notional -> target 0 -> holiday round-trips
s2 = SIGNALS["F7_COMBO"].copy(); s2.columns = U2
_, W2 = PB.run(ret2, s2, cost2, return_weights=True)
d_cont = pnl_from_weights.__wrapped__(W2) if hasattr(pnl_from_weights, "__wrapped__") else None
r0 = ret2.fillna(0.0)
def pnl_w(W, c):
    gross = (W.shift(2) * r0).sum(axis=1); turn = (W.shift(1) - W.shift(2)).abs()
    cs = (turn * c.reindex_like(W).ffill().shift(1)).sum(axis=1)
    return gross - cs, W.abs().sum(axis=1)
cont, _ = pnl_w(W2, cost2)
for C in (100_000, 250_000, 1_000_000, 5_000_000):
    tgt = (W2 * C / notional).replace([np.inf, -np.inf], np.nan).fillna(0.0).to_numpy()
    held = np.zeros(tgt.shape[1]); H = np.zeros_like(tgt)
    for t in range(len(tgt)):
        dev = np.abs(tgt[t] - held)
        trade = dev > 0.5 + 0.1 * np.abs(tgt[t])          # audit V6-B1: protocol says 0.5 contract PLUS 10% (hysteresis)
        held = np.where(trade, np.round(tgt[t]), held)
        H[t] = held
    Wr = pd.DataFrame(H, index=W2.index, columns=U2) * notional.fillna(0.0) / C
    net, lev = pnl_w(Wr, cost2)
    nz = (pd.DataFrame(H, index=W2.index) != 0).sum(axis=1)
    out["G14c"][C] = {"VALIDATION": round(PB.stats(net.loc["2005":"2013"])["sharpe"], 3), "2014_2024_contaminated": round(PB.stats(net.loc["2014":"2024"])["sharpe"], 3),
                      "continuous_VALIDATION": round(PB.stats(cont.loc["2005":"2013"])["sharpe"], 3), "continuous_2014_2024": round(PB.stats(cont.loc["2014":"2024"])["sharpe"], 3),
                      "corr_with_continuous_2014_2024": round(float(net.loc["2014":"2024"].corr(cont.loc["2014":"2024"])), 3),
                      "median_instruments_held_2020": float(nz.loc["2020":"2024"].median()), "ann_vol_2014_2024": round(float(net.loc["2014":"2024"].std() * 16), 3)}
    print(C, out["G14c"][C])
out["G14c_choice"] = choice
if not RUN_A:
    prev = json.loads((ROOT / "results/v6_futures_gen14.json").read_text())
    prev["G14c_superseded_V6-B1"] = prev.get("G14c"); prev["G14c"] = out["G14c"]; prev["G14c_choice"] = choice
    (ROOT / "results/v6_futures_gen14.json").write_text(json.dumps(prev, indent=1, default=float))
    F.append({"kind": "audit", "id": "V6-B1", "note": "G14c integer-contract band coded as max(0.5,10%) instead of protocol '0.5 contract + 10%' -> rounding churn; G14c re-run, old numbers kept as superseded",
              "result": {str(k): v for k, v in out["G14c"].items()}})
    sys.exit(0)
(ROOT / "results/v6_futures_gen14.json").write_text(json.dumps(out, indent=1, default=float))
for name in SIGNALS:
    F.decide(F.Hypothesis(f"G14_BUFFER_{name}", "futures/implementation", "", "", "", "", "", "", PROTO, generation=14),
             "EXPLORATORY" if out["G14a"][name]["adopted_b"] is None else "PROMISING_BUT_UNVALIDATED",
             f"buffer adopted b={out['G14a'][name]['adopted_b']} (implementation layer)", {"protocol": PROTO})
F.append({"kind": "analysis", "stage": "G14c_capital", "result": {str(k): v for k, v in out["G14c"].items()}})
