"""Paper trader v2 (simulation only - never sends orders).

Audit finding A-P1: v1's parity test was partly circular (the paper trader called the same
`build_context`/`noise_area` code as the backtester). v2 re-implements the H3 signal from its written
specification, incrementally, WITHOUT importing qpl.strategies or qpl.features; only the exchange
holiday calendar (data, not logic) is shared. Components:

  DataGuard     - rejects duplicate / out-of-order / malformed bars, flags gaps and stale data
  H3Signal      - clean-room incremental noise-area signal (spec: reports/v3 strategy card)
  RiskManager   - prop rules (EOD-trailing MLL incl. open P&L, optional DLL, consistency, contract cap,
                  flat-by cut-off, kill switch on drift vs backtest expectation)
  SimBroker     - next-bar-open market fills, stop fills at worse of stop/open, slippage, commission,
                  reconciliation record (expected price vs simulated fill)
  PaperRunner   - orchestration, JSONL audit log, checkpoint save/restore (restart-safe)
"""
from __future__ import annotations

import json
import math
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from ..data.calendar import early_closes, holidays

ET = "America/New_York"


@dataclass
class Spec:
    lookback: int = 14
    mult: float = 1.25
    check_min: int = 60
    open_min: int = 570
    close_min: int = 960
    bar_min: int = 15
    cat_stop_sd: float = 1.5
    max_entries_day: int = 6
    sd_window: int = 20
    sd_min_periods: int = 15


class DataGuard:
    def __init__(self, bar_min: int, max_gap_min: int = 120):
        self.last_ts = None
        self.bar_min = bar_min
        self.max_gap = max_gap_min
        self.events: list[dict] = []

    def check(self, ts, o, h, l, c) -> bool:
        ok = True
        if self.last_ts is not None and ts <= self.last_ts:
            self.events.append({"kind": "rejected_bar", "ts": str(ts), "why": "duplicate_or_out_of_order"}); ok = False
        if not (np.isfinite([o, h, l, c]).all() and h >= max(o, c) and l <= min(o, c) and l > 0):
            self.events.append({"kind": "rejected_bar", "ts": str(ts), "why": "malformed_ohlc"}); ok = False
        if ok and self.last_ts is not None:
            gap = (ts - self.last_ts).total_seconds() / 60
            if gap > self.max_gap and not (ts.tz_convert(ET).dayofweek in (6, 0)):
                self.events.append({"kind": "gap_warning", "ts": str(ts), "minutes": gap})
        if ok:
            self.last_ts = ts
        return ok


class H3Signal:
    """Incremental clean-room implementation of the H3 noise-area rules."""

    def __init__(self, spec: Spec):
        self.s = spec
        self.hol = set(holidays()); self.ec = set(early_closes())
        self.rows: list[dict] = []                 # one dict per prior RTH day with >=1 slot value (spec: last N session rows)
        self.daily: list[tuple] = []               # (date, close, complete) per finished RTH day
        self.day = None; self.day_open = math.nan; self.day_first_min = None; self.day_last_min = None
        self.day_valid = False; self.today_slots: dict[int, float] = {}
        self.tp_sum = 0.0; self.tp_n = 0
        self.last_close = math.nan

    # ---- daily state (only completed days)
    def _finish_day(self):
        if self.day is None or self.day_first_min is None:
            return
        complete = self.day_first_min == self.s.open_min and self.day_last_min + self.s.bar_min == self.s.close_min
        self.daily.append((self.day, self.last_close, complete))
        if self.today_slots:
            self.rows.append(dict(self.today_slots))

    def prev_close(self):
        for d, c, comp in reversed(self.daily):
            if comp:
                return c
        return math.nan

    def sd_points(self):
        closes = [c for _, c, _ in self.daily]
        diffs = np.diff(closes)[-self.s.sd_window:]
        return float(np.std(diffs, ddof=1)) if len(diffs) >= self.s.sd_min_periods else math.nan

    def sigma(self, slot):
        """Mean of |close/open-1| at this slot over the last `lookback` prior session rows; all must exist."""
        if len(self.rows) < self.s.lookback:
            return math.nan
        vals = [r.get(slot) for r in self.rows[-self.s.lookback:]]
        if any(v is None for v in vals):
            return math.nan
        return float(np.mean(vals))

    def on_bar(self, ts, o, h, l, c) -> dict:
        e = ts.tz_convert(ET)
        m = e.hour * 60 + e.minute
        d = e.normalize().tz_localize(None)
        s = self.s
        rth = m >= s.open_min and m + s.bar_min <= s.close_min
        out = {"rth": rth, "check": False, "entry": 0, "exit_long": False, "exit_short": False, "sd": math.nan, "flat": False}
        if not rth:
            return out
        if d != self.day:
            self._finish_day()
            self.day = d; self.day_first_min = None; self.today_slots = {}; self.tp_sum = 0.0; self.tp_n = 0
            self.day_valid = d not in self.hol and d not in self.ec and e.dayofweek < 5
            self.day_open = math.nan
        if not self.day_valid:
            return out
        if self.day_first_min is None:
            self.day_first_min = m
            self.day_open = o if m == s.open_min else math.nan
        self.day_last_min = m
        self.last_close = c
        slot = (m - s.open_min) // s.bar_min
        if np.isfinite(self.day_open):
            self.today_slots[slot] = abs(c / self.day_open - 1)
        self.tp_sum += (h + l + c) / 3; self.tp_n += 1
        twap = self.tp_sum / self.tp_n
        out["sd"] = self.sd_points()
        out["flat"] = m + s.bar_min == s.close_min
        end = m + s.bar_min
        if end % s.check_min != 0 or end < s.open_min + 30:
            return out
        sig = self.sigma(slot); pc = self.prev_close(); op = self.day_open
        if not (np.isfinite(sig) and np.isfinite(pc) and np.isfinite(op) and np.isfinite(out["sd"])):
            return out
        ub = max(op, pc) * (1 + s.mult * sig); lb = min(op, pc) * (1 - s.mult * sig)
        out["check"] = True
        if end <= s.close_min - 30:
            out["entry"] = 1 if c > ub else (-1 if c < lb else 0)
        out["exit_long"] = c < max(ub, twap)
        out["exit_short"] = c > min(lb, twap)
        return out


@dataclass
class Account:
    start: float = 50_000.0
    mll: float = 2_000.0
    target: float = 3_000.0
    consistency: float = 0.55
    dll: float | None = None
    lock_at_start: bool = True
    balance: float = 50_000.0
    floor: float = 48_000.0
    eod_high: float = 50_000.0
    best_day: float = 0.0
    day_pnl: float = 0.0
    status: str = "ACTIVE"


class RiskManager:
    def __init__(self, acct: Account, max_contracts=50, kill_z=-2.0, kill_min_trades=30, exp_mean=27.6, exp_sd=243.0):
        self.a = acct; self.max_contracts = max_contracts
        self.kill_z, self.kill_min, self.mu, self.sd = kill_z, kill_min_trades, exp_mean, exp_sd
        self.kill = False; self.halt_today = False

    def allow_entry(self) -> bool:
        return self.a.status == "ACTIVE" and not self.kill and not self.halt_today

    def size(self, sd_pts, point_value, budget):
        if budget is None or not np.isfinite(sd_pts):
            return 1
        return int(min(max(1, math.floor(budget / (sd_pts * point_value))), self.max_contracts))

    def intrabar(self, unreal_worst) -> str | None:
        if self.a.balance + self.a.day_pnl + unreal_worst <= self.a.floor:
            return "MLL"
        if self.a.dll is not None and self.a.day_pnl + unreal_worst <= -self.a.dll:
            return "DLL"
        return None

    def end_of_day(self):
        a = self.a
        a.balance += a.day_pnl
        a.best_day = max(a.best_day, a.day_pnl)
        prof = a.balance - a.start
        if a.balance <= a.floor:
            a.status = "FAILED_MLL"
        elif a.status == "ACTIVE" and prof >= max(a.target, a.best_day / a.consistency):
            a.status = "PASSED"
        if a.balance > a.eod_high:
            a.eod_high = a.balance
            nf = a.eod_high - a.mll
            a.floor = max(a.floor, min(nf, a.start) if a.lock_at_start else nf)
        a.day_pnl = 0.0; self.halt_today = False

    def monitor(self, per_contract_pnls: list[float]) -> float | None:
        n = len(per_contract_pnls)
        if n == 0:
            return None
        z = (sum(per_contract_pnls) - n * self.mu) / (self.sd * math.sqrt(n))
        if n >= self.kill_min and z < self.kill_z:
            self.kill = True
        return z


class SimBroker:
    def __init__(self, tick, point_value, commission_rt, slip_ticks=1.0):
        self.tick, self.pv, self.comm, self.slip = tick, point_value, commission_rt, slip_ticks * tick
        self.pos = 0; self.qty = 0; self.entry_px = math.nan; self.stop = math.nan; self.entry_ts = None
        self.recon: list[dict] = []

    def market(self, ts, ref_open, side, qty=None, expected=None, kind="entry"):
        px = ref_open + self.slip * side
        self.recon.append({"ts": str(ts), "kind": kind, "expected_px": expected, "sim_fill": px, "diff": None if expected is None else px - expected})
        return px

    def pnl(self, exit_px):
        return self.qty * ((exit_px - self.entry_px) * self.pos * self.pv - self.comm)


@dataclass
class RunnerConfig:
    symbol: str = "MNQ"
    tick: float = 0.25
    point_value: float = 2.0
    commission_rt: float = 0.74
    slip_ticks: float = 1.0
    risk_budget: float | None = None
    max_contracts: int = 50
    account: dict = field(default_factory=dict)
    kill_z: float = -2.0
    kill_min_trades: int = 30


class PaperRunner:
    def __init__(self, cfg: RunnerConfig, log_dir: Path, spec: Spec | None = None):
        self.cfg = cfg
        self.spec = spec or Spec()
        self.guard = DataGuard(self.spec.bar_min)
        self.sig = H3Signal(self.spec)
        self.risk = RiskManager(Account(**cfg.account) if cfg.account else Account(), cfg.max_contracts,
                                kill_z=cfg.kill_z, kill_min_trades=cfg.kill_min_trades)
        self.brk = SimBroker(cfg.tick, cfg.point_value, cfg.commission_rt, cfg.slip_ticks)
        self.pend_entry = None; self.pend_exit = False; self.entries_today = 0; self.cur_day = None
        self.trades: list[dict] = []
        self.log = Path(log_dir) / f"paper_v2_{cfg.symbol}.jsonl"
        self.log.parent.mkdir(parents=True, exist_ok=True)

    def _emit(self, kind, **kw):
        with open(self.log, "a") as f:
            f.write(json.dumps({"kind": kind, "wall": time.strftime("%Y-%m-%dT%H:%M:%S"), **kw}, default=str) + "\n")

    def _close(self, ts, px, reason):
        b = self.brk
        pnl = b.pnl(px)
        self.risk.a.day_pnl += pnl
        t = {"entry_ts": b.entry_ts, "exit_ts": ts, "dir": b.pos, "qty": b.qty, "entry_px": b.entry_px, "exit_px": px, "reason": reason, "pnl_usd": pnl}
        self.trades.append(t); self._emit("trade", **t)
        b.pos, b.qty, b.entry_px, b.stop = 0, 0, math.nan, math.nan

    def on_bar(self, ts, o, h, l, c):
        if not self.guard.check(ts, o, h, l, c):
            self._emit("data_quality", **self.guard.events[-1]); return
        b = self.brk
        e = ts.tz_convert(ET); day = e.normalize().tz_localize(None)
        if day != self.cur_day:
            self.cur_day = day; self.entries_today = 0
        exited = False
        if self.pend_exit and b.pos != 0:
            self._close(ts, b.market(ts, o, -b.pos, kind="exit"), "SIGNAL"); exited = True
        self.pend_exit = False
        if self.pend_entry and b.pos == 0 and not exited and self.risk.allow_entry():
            pe = self.pend_entry
            b.pos, b.qty = pe["dir"], pe["qty"]
            b.entry_px = b.market(ts, o, pe["dir"], expected=pe["signal_close"], kind="entry")
            b.entry_ts = ts
            # protective stop measured from the bar open (spec convention shared with the backtester)
            b.stop = o - b.pos * pe["stop_dist"] if np.isfinite(pe["stop_dist"]) else math.nan
            self.entries_today += 1
            self._emit("fill", ts=ts, dir=b.pos, qty=b.qty, px=b.entry_px)
        self.pend_entry = None
        if b.pos != 0:
            if np.isfinite(b.stop) and ((b.pos > 0 and l <= b.stop) or (b.pos < 0 and h >= b.stop)):
                px = min(b.stop, o) - b.slip if b.pos > 0 else max(b.stop, o) + b.slip
                self._close(ts, px, "STOP")
            else:
                worst = l if b.pos > 0 else h
                breach = self.risk.intrabar(b.qty * ((worst - b.entry_px) * b.pos * b.pv - b.comm))
                if breach:
                    self._emit("rule_breach", rule=breach, ts=ts)
                    self._close(ts, worst - b.slip * b.pos, f"{breach}_LIQUIDATION")
                    if breach == "MLL":
                        self.risk.a.status = "FAILED_MLL"
                    else:
                        self.risk.halt_today = True
        s = self.sig.on_bar(ts, o, h, l, c)
        if s["flat"]:
            if b.pos != 0:
                self._close(ts, c - b.slip * b.pos, "FLAT_EOD")
            self.pend_entry = None; self.pend_exit = False
            self.risk.end_of_day()
            z = self.risk.monitor([t["pnl_usd"] / t["qty"] for t in self.trades])
            self._emit("day", date=day, balance=self.risk.a.balance, floor=self.risk.a.floor, status=self.risk.a.status, drift_z=z,
                       kill=self.risk.kill)
            return
        if not s["check"]:
            return
        if b.pos != 0 and ((b.pos > 0 and s["exit_long"]) or (b.pos < 0 and s["exit_short"])):
            self.pend_exit = True
        if b.pos == 0 and s["entry"] != 0 and self.entries_today < self.spec.max_entries_day and self.risk.allow_entry():
            q = self.risk.size(s["sd"], self.cfg.point_value, self.cfg.risk_budget)
            self.pend_entry = {"dir": s["entry"], "qty": q, "stop_dist": self.spec.cat_stop_sd * s["sd"], "signal_close": c}
            self._emit("signal", ts=ts, dir=s["entry"], qty=q)

    # ---- restart-safe checkpointing (pickle-free JSON of plain state)
    def checkpoint(self, path: Path):
        sig = self.sig
        st = {"spec": asdict(self.spec), "account": asdict(self.risk.a), "kill": self.risk.kill,
              "broker": {"pos": self.brk.pos, "qty": self.brk.qty, "entry_px": self.brk.entry_px, "stop": self.brk.stop,
                         "entry_ts": str(self.brk.entry_ts) if self.brk.entry_ts is not None else None},
              "pend_entry": self.pend_entry, "pend_exit": self.pend_exit, "entries_today": self.entries_today,
              "cur_day": str(self.cur_day) if self.cur_day is not None else None, "guard_last": str(self.guard.last_ts) if self.guard.last_ts is not None else None,
              "signal": {"rows": [{str(k): v for k, v in r.items()} for r in sig.rows],
                         "daily": [(str(d), c, comp) for d, c, comp in sig.daily], "day": str(sig.day) if sig.day is not None else None,
                         "day_open": sig.day_open, "day_first_min": sig.day_first_min, "day_last_min": sig.day_last_min,
                         "day_valid": sig.day_valid, "today_slots": {str(k): v for k, v in sig.today_slots.items()},
                         "tp_sum": sig.tp_sum, "tp_n": sig.tp_n, "last_close": sig.last_close},
              "trades": self.trades}
        Path(path).write_text(json.dumps(st, default=str))

    @classmethod
    def restore(cls, path: Path, cfg: RunnerConfig, log_dir: Path) -> "PaperRunner":
        st = json.loads(Path(path).read_text())
        r = cls(cfg, log_dir, Spec(**st["spec"]))
        r.risk.a = Account(**st["account"]); r.risk.kill = st["kill"]
        bk = st["broker"]; r.brk.pos, r.brk.qty, r.brk.entry_px, r.brk.stop = bk["pos"], bk["qty"], bk["entry_px"], bk["stop"]
        r.brk.entry_ts = pd.Timestamp(bk["entry_ts"]) if bk["entry_ts"] else None
        r.pend_entry, r.pend_exit, r.entries_today = st["pend_entry"], st["pend_exit"], st["entries_today"]
        r.cur_day = pd.Timestamp(st["cur_day"]) if st["cur_day"] else None
        r.guard.last_ts = pd.Timestamp(st["guard_last"]) if st["guard_last"] else None
        s = st["signal"]; sig = r.sig
        sig.rows = [{int(k): v for k, v in r.items()} for r in s["rows"]]
        sig.daily = [(pd.Timestamp(d), c, comp) for d, c, comp in s["daily"]]
        sig.day = pd.Timestamp(s["day"]) if s["day"] else None
        sig.day_open, sig.day_first_min, sig.day_last_min = s["day_open"], s["day_first_min"], s["day_last_min"]
        sig.day_valid, sig.today_slots = s["day_valid"], {int(k): v for k, v in s["today_slots"].items()}
        sig.tp_sum, sig.tp_n, sig.last_close = s["tp_sum"], s["tp_n"], s["last_close"]
        r.trades = st["trades"]
        return r


def replay(df: pd.DataFrame, cfg: RunnerConfig, log_dir: Path, spec: Spec | None = None) -> PaperRunner:
    r = PaperRunner(cfg, log_dir, spec)
    for ts, row in df.iterrows():
        r.on_bar(ts, row.open, row.high, row.low, row.close)
    return r
