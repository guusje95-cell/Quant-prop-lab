"""Futures paper book for F9_SLEEVE_RP (config/f9_spec.json). SIMULATION ONLY: never connects to a broker or sends orders.

Each run: rebuild the panel from a pysystemtrade-format data directory supplied by the user, recompute frozen F9 weights
(stateless, so no signal drift), mark held contracts to market since the last run, fill yesterday's simulated orders at the
latest close, then compute today's target contracts (integer, 0.5 + 10% band) and record them as orders for the next run.
Guards: stale instruments (no new price for > 5 days) are not traded; |daily return| > 25% is flagged; missing FX blocks trading.
Kill rules from the spec: drawdown > 25% flattens and stops; drift z < -2 after 252 days stops."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from ..data import futures_panel as FP
from ..strategies import f9

SPEC = json.loads((Path(__file__).resolve().parents[3] / "config" / "f9_spec.json").read_text())


class FuturesPaperBook:
    def __init__(self, capital: float, state_path: str | Path, log_path: str | Path | None = None):
        self.state_path = Path(state_path)
        self.log_path = Path(log_path) if log_path else self.state_path.with_suffix(".log.jsonl")
        if self.state_path.exists():
            self.s = json.loads(self.state_path.read_text())
        else:
            self.s = {"capital0": capital, "equity": capital, "peak": capital, "held": {}, "pending": {}, "last_date": None,
                      "days": 0, "killed": None, "history": []}

    def _log(self, ev):
        with open(self.log_path, "a") as f:
            f.write(json.dumps(ev, default=str) + "\n")

    def save(self):
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.s, default=str)); tmp.replace(self.state_path)

    def step(self, panel: dict, U: list[str], members: dict[str, str]) -> dict:
        names = [members[k] for k in U]
        ret = panel["ret"][names]; cost = panel["cost"][names]; cy = panel["carry"][names]
        T = ret.index[-1]
        if self.s["last_date"] and pd.Timestamp(self.s["last_date"]) >= T:
            return {"status": "no new data", "last_date": self.s["last_date"]}
        notional = FP.contract_notional(panel, names)
        cfg = FP.meta()
        # 1) mark to market held contracts from last_date to T: P&L = contracts * pointsize * fx * sum(ret_d * PRICE_{d-1})
        pnl = 0.0
        if self.s["last_date"]:
            a = pd.Timestamp(self.s["last_date"])
            for m, c in self.s["held"].items():
                if c == 0 or m not in ret.columns:
                    continue
                r = ret[m].loc[a:].iloc[1:].fillna(0.0)
                px_prev = panel["price"][m].ffill().shift(1).loc[r.index]
                fx = notional[m].loc[r.index] / (panel["price"][m].abs().ffill().loc[r.index] * cfg.loc[m, "Pointsize"])
                pnl += float((c * cfg.loc[m, "Pointsize"] * fx * r * px_prev).sum())
        # 2) fill pending orders at T close (simulated): cost = |contracts| * cost_fraction * notional
        fill_cost = 0.0
        for m, dq in self.s["pending"].items():
            if m in notional.columns and np.isfinite(notional[m].iloc[-1]):
                fill_cost += abs(dq) * float(cost[m].ffill().iloc[-1]) * float(notional[m].iloc[-1])
                self.s["held"][m] = self.s["held"].get(m, 0) + dq
                self._log({"kind": "fill", "date": str(T.date()), "instrument": m, "contracts": dq, "price": float(panel["price"][m].ffill().iloc[-1])})
        self.s["pending"] = {}
        eq = self.s["equity"] + pnl - fill_cost
        self.s["peak"] = max(self.s["peak"], eq)
        self.s["days"] += 1
        flags = []
        dd = eq / self.s["peak"] - 1
        if dd < -SPEC["risk_limits"]["kill_drawdown"]:
            self.s["killed"] = "max_drawdown"
        if self.s["days"] >= 252 and not self.s["killed"]:
            n = self.s["days"]; mu = SPEC["expectation_for_monitoring"]["sharpe"] * 0.10 / 256; sd = 0.10 / math.sqrt(256)
            z = (math.log(eq / self.s["capital0"]) - n * mu) / (sd * math.sqrt(n))
            if z < -2.0:
                self.s["killed"] = "drift_vs_expectation"
        # 3) target contracts
        W = f9.weights(ret, cost, cy).iloc[-1]
        gross = float(W.abs().sum())
        if gross > SPEC["risk_limits"]["gross_notional_max"]:
            W = W * SPEC["risk_limits"]["gross_notional_max"] / gross; flags.append("gross_cap")
        last_obs = ret.apply(lambda s: s.last_valid_index())
        orders = {}
        for m in names:
            stale = last_obs[m] is None or (T - last_obs[m]).days > 5
            if abs(ret[m].iloc[-1]) > 0.25 if np.isfinite(ret[m].iloc[-1]) else False:
                flags.append(f"big_move:{m}")
            held = self.s["held"].get(m, 0)
            if self.s["killed"]:
                tgt = 0.0
            elif stale or not np.isfinite(notional[m].iloc[-1]) or notional[m].iloc[-1] <= 0:
                continue
            else:
                tgt = float(W[m]) * eq / float(notional[m].iloc[-1])
            if abs(tgt - held) > 0.5 + 0.1 * abs(tgt):
                orders[m] = int(round(tgt)) - held
        self.s["pending"] = {m: q for m, q in orders.items() if q != 0}
        self.s.update({"equity": eq, "last_date": str(T.date())})
        rec = {"date": str(T.date()), "equity": eq, "pnl": pnl, "costs": fill_cost, "drawdown": dd, "orders": len(self.s["pending"]),
               "instruments_held": sum(1 for v in self.s["held"].values() if v), "gross_target": gross, "flags": flags, "killed": self.s["killed"]}
        self.s["history"].append(rec)
        self._log({"kind": "step", **rec})
        self.save()
        return rec
