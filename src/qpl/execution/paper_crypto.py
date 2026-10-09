"""Crypto paper trader (simulation only - never connects to an exchange, never sends orders).

Implements the frozen CT1 trend ensemble INCREMENTALLY from its written specification, without importing
qpl.strategies or qpl.backtesting (non-circular: tests compare it against the research implementation).

Spec (CT1, frozen 2026-10-09, config/ct1_protocol.json):
  daily UTC bars; at each completed bar t:
    vol_t   = sample std (ddof=1) of the last 30 daily log close-to-close returns (>= 15 required) * sqrt(365)
    TSMOM_L = sign(ln C_t - ln C_{t-L}) for L in (20, 60, 120)                                 (0 if unavailable)
    DONCH_N : flat -> long if C_t > max(H_{t-N..t-1}); flat -> short if C_t < min(L_{t-N..t-1});
              long -> flat if C_t < min(L_{t-X..t-1}); short -> flat if C_t > max(H_{t-X..t-1}); X = N // 2; N in (20, 55)
    leg     = clip(sign * target_vol / vol_t, -1, 1)  (0 if vol unavailable)
    w_t     = mean of the 5 legs  (research book: target_vol = 0.40)
  execution at the next bar's open.

Accounts are kept SEPARATE:
  SpotAccount  - long-only (negative targets clipped to 0), fully paid, no funding, no liquidation.
  PerpAccount  - long/short linear USDT-margined perp, funding settled every 8h (-qty * mark * rate),
                 isolated margin with leverage cap, maintenance-margin liquidation checked on bar extremes.
"""
from __future__ import annotations

import json
import math
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd


# ------------------------------------------------------------------ spec + signal
@dataclass
class CT1Spec:
    tsmom: tuple = (20, 60, 120)
    donchian: tuple = (20, 55)
    target_vol: float = 0.40
    vol_lb: int = 30
    vol_min: int = 15
    ann: float = 365.0


class CT1Signal:
    def __init__(self, spec: CT1Spec = CT1Spec()):
        self.s = spec
        n = max(max(spec.tsmom), max(spec.donchian)) + 2
        self.c: deque = deque(maxlen=n + 1)
        self.h: deque = deque(maxlen=n + 1)
        self.l: deque = deque(maxlen=n + 1)
        self.state = {N: 0 for N in spec.donchian}

    def _vol(self) -> float:
        c = np.log(np.asarray(self.c, float))
        r = np.diff(c)[-self.s.vol_lb:]
        if len(r) < self.s.vol_min:
            return math.nan
        return float(np.std(r, ddof=1) * math.sqrt(self.s.ann))

    def update(self, high: float, low: float, close: float) -> float:
        """Feed one COMPLETED daily bar; returns the target weight for the next bar."""
        self.c.append(close); self.h.append(high); self.l.append(low)
        C = list(self.c); H = list(self.h); Lw = list(self.l)
        vol = self._vol()
        legs = []
        for L in self.s.tsmom:
            sgn = float(np.sign(math.log(C[-1]) - math.log(C[-1 - L]))) if len(C) > L else 0.0
            legs.append(sgn)
        for N in self.s.donchian:
            X = max(2, N // 2)
            cur = self.state[N]
            if len(C) > N:
                hi, lo = max(H[-1 - N:-1]), min(Lw[-1 - N:-1])
                if cur == 0:
                    cur = 1 if C[-1] > hi else (-1 if C[-1] < lo else 0)
                elif len(C) > X:
                    xh, xl = max(H[-1 - X:-1]), min(Lw[-1 - X:-1])
                    if cur == 1 and C[-1] < xl:
                        cur = 0
                    elif cur == -1 and C[-1] > xh:
                        cur = 0
            self.state[N] = cur
            legs.append(float(cur))
        if not np.isfinite(vol) or vol <= 0:
            return 0.0
        return float(np.mean([max(-1.0, min(1.0, g * self.s.target_vol / vol)) for g in legs]))


# ------------------------------------------------------------------ data guard
class DataGuard:
    def __init__(self, bar: pd.Timedelta = pd.Timedelta(days=1)):
        self.bar = bar
        self.last = None
        self.c_prev: float | None = None
        self.events: list[dict] = []

    def check(self, ts: pd.Timestamp, o, h, l, c) -> bool:
        if self.last is not None and ts <= self.last:
            self.events.append({"kind": "rejected_bar", "ts": str(ts), "why": "duplicate_or_out_of_order"}); return False
        vals = np.array([o, h, l, c], float)
        if not (np.isfinite(vals).all() and l > 0 and h >= max(o, c) and l <= min(o, c)):
            self.events.append({"kind": "rejected_bar", "ts": str(ts), "why": "malformed_ohlc"}); return False
        if self.last is not None and ts - self.last > self.bar:
            self.events.append({"kind": "gap", "ts": str(ts), "missing_bars": int((ts - self.last) / self.bar) - 1})
        if self.last is not None and self.c_prev and abs(math.log(c / self.c_prev)) > 0.6:
            self.events.append({"kind": "suspicious_move", "ts": str(ts), "logret": math.log(c / self.c_prev)})
        self.last, self.c_prev = ts, c
        return True


# ------------------------------------------------------------------ accounts
@dataclass
class Fill:
    ts: str
    side: str
    qty: float
    expected_px: float
    fill_px: float
    fee: float


@dataclass
class SpotAccount:
    cash: float = 10_000.0
    qty: float = 0.0
    fee_bps: float = 10.0
    slip_bps: float = 5.0
    kind: str = "spot"
    fills: list = field(default_factory=list)

    def equity(self, px: float) -> float:
        return self.cash + self.qty * px

    def clip_target(self, w: float) -> float:
        return max(0.0, min(1.0, w))                      # spot: no shorts, no leverage

    def rebalance(self, ts, target_w: float, px: float) -> Fill | None:
        w = self.clip_target(target_w)
        eq = self.equity(px)
        dq = w * eq / px - self.qty
        if abs(dq * px) < 1e-6 * max(eq, 1):
            return None
        fpx = px * (1 + math.copysign(self.slip_bps, dq) / 1e4)
        fee = abs(dq) * fpx * self.fee_bps / 1e4
        self.cash -= dq * fpx + fee
        self.qty += dq
        f = Fill(str(ts), "buy" if dq > 0 else "sell", dq, px, fpx, fee)
        self.fills.append(asdict(f))
        return f

    def settle_funding(self, ts, rate: float, mark: float) -> float:
        return 0.0

    def liquidation_check(self, ts, low: float, high: float) -> bool:
        return False


@dataclass
class PerpAccount:
    cash: float = 10_000.0                                # margin balance (realised)
    qty: float = 0.0
    entry: float = 0.0                                    # average entry price
    fee_bps: float = 5.0
    slip_bps: float = 2.0
    max_leverage: float = 1.0
    maint_margin: float = 0.005
    kind: str = "perp"
    fills: list = field(default_factory=list)
    funding_paid: float = 0.0
    liquidated: bool = False

    def equity(self, px: float) -> float:
        return self.cash + self.qty * (px - self.entry)

    def clip_target(self, w: float) -> float:
        return max(-self.max_leverage, min(self.max_leverage, w))

    def rebalance(self, ts, target_w: float, px: float) -> Fill | None:
        if self.liquidated:
            return None
        w = self.clip_target(target_w)
        eq = self.equity(px)
        dq = w * eq / px - self.qty
        if abs(dq * px) < 1e-6 * max(eq, 1):
            return None
        fpx = px * (1 + math.copysign(self.slip_bps, dq) / 1e4)
        fee = abs(dq) * fpx * self.fee_bps / 1e4
        # realise P&L on the reduced part, re-average entry on the increased part
        new_q = self.qty + dq
        if self.qty != 0 and (np.sign(dq) != np.sign(self.qty)):
            closed = min(abs(dq), abs(self.qty)) * np.sign(self.qty)
            self.cash += closed * (fpx - self.entry)
            if np.sign(new_q) != np.sign(self.qty) and new_q != 0:
                self.entry = fpx
        elif new_q != 0:
            self.entry = (self.qty * self.entry + dq * fpx) / new_q
        if new_q == 0:
            self.entry = 0.0
        self.qty = new_q
        self.cash -= fee
        f = Fill(str(ts), "buy" if dq > 0 else "sell", dq, px, fpx, fee)
        self.fills.append(asdict(f))
        return f

    def settle_funding(self, ts, rate: float, mark: float) -> float:
        pay = self.qty * mark * rate                      # long pays positive funding
        self.cash -= pay
        self.funding_paid += pay
        return -pay

    def liquidation_check(self, ts, low: float, high: float) -> bool:
        if self.qty == 0 or self.liquidated:
            return False
        worst = low if self.qty > 0 else high
        if self.equity(worst) <= self.maint_margin * abs(self.qty) * worst:
            self.cash = self.equity(worst) - abs(self.qty) * worst * 0.005   # liquidation fee
            self.qty, self.entry, self.liquidated = 0.0, 0.0, True
            return True
        return False


# ------------------------------------------------------------------ risk manager
@dataclass
class RiskConfig:
    book_scale: float = 0.30          # 0.30 x the 40%-vol research book ~= 12% annual vol (results/v4_ct1_risk.json)
    max_dd_kill: float = 0.25         # flatten and stop if equity falls 25% below its peak
    max_daily_loss: float = 0.06      # flatten for the day if the day's loss exceeds 6%
    drift_z_kill: float = -2.5        # stop if cumulative return z-score vs expected (post-dev mu, sigma) < -2.5 ...
    drift_min_days: int = 90          # ... after at least 90 days
    exp_mu_daily: float = 0.12563 / 365 * 0.30
    exp_sd_daily: float = 0.29895 / math.sqrt(365) * 0.30


class RiskManager:
    def __init__(self, cfg: RiskConfig):
        self.cfg = cfg
        self.peak = None
        self.killed = None
        self.start_eq = None
        self.days = 0

    def target(self, w_signal: float) -> float:
        return 0.0 if self.killed else w_signal * self.cfg.book_scale

    def end_of_day(self, eq: float, eq_prev: float) -> str | None:
        self.start_eq = self.start_eq or eq_prev
        self.peak = max(self.peak or eq, eq)
        self.days += 1
        if self.killed:
            return None
        if eq / self.peak - 1 < -self.cfg.max_dd_kill:
            self.killed = "max_drawdown"; return self.killed
        if eq / eq_prev - 1 < -self.cfg.max_daily_loss:
            return "daily_loss_flatten"
        if self.days >= self.cfg.drift_min_days:
            n = self.days
            z = (math.log(eq / self.start_eq) - n * self.cfg.exp_mu_daily) / (self.cfg.exp_sd_daily * math.sqrt(n))
            if z < self.cfg.drift_z_kill:
                self.killed = "drift_vs_expectation"; return self.killed
        return None


# ------------------------------------------------------------------ runner
class CryptoPaperRunner:
    """Feeds completed daily bars (+ optional funding prints) through guard -> signal -> risk -> broker.
    Orders decided at bar t's close are filled at bar t+1's open (passed with the next bar)."""

    def __init__(self, account, risk: RiskConfig = RiskConfig(), spec: CT1Spec = CT1Spec(), log_path: str | Path | None = None):
        self.acct, self.sig, self.guard, self.risk = account, CT1Signal(spec), DataGuard(), RiskManager(risk)
        self.pending_w: float | None = None
        self.eq_prev: float | None = None
        self.log_path = Path(log_path) if log_path else None
        self.history: list[dict] = []
        self.funding_q: list[tuple] = []

    def _log(self, ev: dict):
        if self.log_path:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(ev, default=str) + "\n")

    def add_funding(self, ts: pd.Timestamp, rate: float, mark: float | None = None):
        self.funding_q.append((ts, rate, mark))

    def warmup(self, ts: pd.Timestamp, o: float, h: float, l: float, c: float):
        """Feed history BEFORE paper trading starts: updates guard + signal state only (no orders, no equity)."""
        if self.guard.check(ts, o, h, l, c):
            self.pending_w = self.risk.target(self.sig.update(h, l, c))

    def on_bar(self, ts: pd.Timestamp, o: float, h: float, l: float, c: float):
        if not self.guard.check(ts, o, h, l, c):
            self._log(self.guard.events[-1]); return
        if self.pending_w is not None:                    # execute yesterday's decision at today's open
            f = self.acct.rebalance(ts, self.pending_w, o)
            if f:
                self._log({"kind": "fill", **asdict(f)})
        # funding prints that fall inside this bar (held position pays/receives)
        end = ts + pd.Timedelta(days=1)
        due = [x for x in self.funding_q if ts < x[0] <= end]
        self.funding_q = [x for x in self.funding_q if x[0] > end]
        for fts, rate, mark in due:
            self.acct.settle_funding(fts, rate, mark if mark else c)
        if self.acct.liquidation_check(ts, l, h):
            self._log({"kind": "liquidation", "ts": str(ts)})
        eq = self.acct.equity(c)
        w_sig = self.sig.update(h, l, c)
        flag = self.risk.end_of_day(eq, self.eq_prev) if self.eq_prev else None
        w = 0.0 if flag in ("daily_loss_flatten",) else self.risk.target(w_sig)
        if flag:
            self._log({"kind": "risk", "ts": str(ts), "flag": flag})
        self.pending_w = w
        self.history.append({"ts": ts, "equity": eq, "w_signal": w_sig, "w_target": w, "qty": self.acct.qty})
        self.eq_prev = eq

    # ---- checkpointing (restart-safe)
    def checkpoint(self) -> dict:
        return {"acct": {k: v for k, v in asdict(self.acct).items()} | {"_cls": type(self.acct).__name__},
                "sig": {"c": list(self.sig.c), "h": list(self.sig.h), "l": list(self.sig.l), "state": {str(k): v for k, v in self.sig.state.items()}},
                "guard_last": str(self.guard.last) if self.guard.last is not None else None, "guard_c_prev": self.guard.c_prev,
                "risk": {"peak": self.risk.peak, "killed": self.risk.killed, "start_eq": self.risk.start_eq, "days": self.risk.days},
                "pending_w": self.pending_w, "eq_prev": self.eq_prev,
                "funding_q": [(str(a), b, m) for a, b, m in self.funding_q]}

    @classmethod
    def restore(cls, ck: dict, risk: RiskConfig = RiskConfig(), spec: CT1Spec = CT1Spec(), log_path=None):
        a = dict(ck["acct"]); kind = a.pop("_cls")
        acct = (PerpAccount if kind == "PerpAccount" else SpotAccount)(**a)
        r = cls(acct, risk, spec, log_path)
        r.sig.c.extend(ck["sig"]["c"]); r.sig.h.extend(ck["sig"]["h"]); r.sig.l.extend(ck["sig"]["l"])
        r.sig.state = {int(k): v for k, v in ck["sig"]["state"].items()}
        r.guard.last = pd.Timestamp(ck["guard_last"]) if ck["guard_last"] else None
        r.guard.c_prev = ck["guard_c_prev"]
        for k, v in ck["risk"].items():
            setattr(r.risk, k, v)
        r.pending_w, r.eq_prev = ck["pending_w"], ck["eq_prev"]
        r.funding_q = [(pd.Timestamp(a), b, m) for a, b, m in ck["funding_q"]]
        return r
