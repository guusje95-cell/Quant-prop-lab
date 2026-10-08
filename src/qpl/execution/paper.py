"""Event-driven PAPER trader for the frozen H3 candidate (noise-area intraday momentum).

* Consumes completed bars one at a time (replay CSV / any BarSource).
* Recomputes signals using ONLY bars received so far (no future access is possible).
* Simulates orders and fills with the same documented assumptions as the backtester
  (market orders at the next bar open +/- slippage, stops at the worse of stop/open, flat at 16:00 ET).
* Tracks prop-firm rules in real time (EOD-trailing MLL incl. unrealized P&L, optional DLL,
  consistency target, position limit, flat-by cut-off).
* Writes an append-only JSONL audit log (signal, order, fill, trade, day, rule events) with both
  the bar timestamp and the wall-clock processing time.
* Compares realised behaviour with the backtest expectation and raises a kill-switch flag.

NO ORDERS ARE EVER SENT TO A BROKER. Real-money deployment requires explicit human approval and
a separate, reviewed execution adapter.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from ..instruments import Instrument, get
from ..strategies import index_intraday as SI

ET = "America/New_York"


@dataclass
class PaperConfig:
    symbol: str = "MNQ"
    bar_minutes: int = 15
    params: dict = field(default_factory=lambda: dict(lookback=14, mult=1.25, trail="band_mean", check_min=60,
                                                      cat_stop_sd=1.5, max_trades=6))
    risk_budget_per_sd: float | None = 500.0     # USD per 1 daily sd of the underlying; None -> fixed contracts
    fixed_contracts: int = 1
    max_contracts: int = 50
    slip_ticks: float = 1.0
    history_days: int = 70
    # prop rules (Topstep 50K defaults)
    start_balance: float = 50_000.0
    mll: float = 2_000.0
    lock_at_start: bool = True
    dll: float | None = None
    target: float = 3_000.0
    consistency: float = 0.55
    # expectation (per 1 MNQ, from dev+OOS backtest) for drift monitoring
    exp_trade_mean: float = 27.6
    exp_trade_sd: float = 243.0
    exp_daily_mean: float = 14.3
    exp_daily_sd: float = 172.9
    kill_z: float = -2.0          # kill switch if cumulative P&L z-score < kill_z after min trades
    kill_min_trades: int = 30


class PaperTrader:
    def __init__(self, cfg: PaperConfig, log_dir: Path):
        self.cfg = cfg
        self.inst: Instrument = get(cfg.symbol)
        self.bars = pd.DataFrame(columns=["open", "high", "low", "close", "volume"], dtype=float)
        self.log_path = Path(log_dir) / f"paper_{cfg.symbol}_{time.strftime('%Y%m%d_%H%M%S')}.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        # position / orders
        self.pos = 0
        self.qty = 0
        self.entry_px = math.nan
        self.entry_ts = None
        self.stop = math.nan
        self.mae = 0.0
        self.pending_entry = None      # dict(dir, qty, stop_dist, signal_ts)
        self.pending_exit = False
        self.trades_today = 0
        self.cur_date = None
        # account
        self.balance = cfg.start_balance
        self.eod_high = cfg.start_balance
        self.floor = cfg.start_balance - cfg.mll
        self.day_pnl = 0.0
        self.best_day = 0.0
        self.status = "ACTIVE"
        self.halted_today = False
        self.trades: list[dict] = []
        self.days: list[dict] = []
        self.kill = False

    # ------------------------------------------------------------------ logging
    def _log(self, kind: str, **kw):
        rec = {"kind": kind, "wall": time.strftime("%Y-%m-%dT%H:%M:%S"), **kw}
        with open(self.log_path, "a") as f:
            f.write(json.dumps(rec, default=str) + "\n")

    # ------------------------------------------------------------------ helpers
    def _slip(self) -> float:
        return self.cfg.slip_ticks * self.inst.tick_size

    def _close_position(self, ts, px, reason):
        pnl_pts = (px - self.entry_px) * self.pos
        pnl = self.qty * (pnl_pts * self.inst.point_value - self.inst.commission_rt)
        self.balance += pnl
        self.day_pnl += pnl
        tr = {"entry_ts": self.entry_ts, "exit_ts": ts, "dir": self.pos, "qty": self.qty, "entry_px": self.entry_px,
              "exit_px": px, "reason": reason, "pnl_usd": pnl, "mae_pts": self.mae}
        self.trades.append(tr)
        self._log("trade", **tr)
        self.pos, self.qty, self.entry_px, self.stop, self.mae = 0, 0, math.nan, math.nan, 0.0

    def _check_realtime_rules(self, ts, worst_px):
        if self.pos == 0:
            return
        unreal = (worst_px - self.entry_px) * self.pos * self.qty * self.inst.point_value - self.qty * self.inst.commission_rt
        eq_low = self.balance + unreal
        if eq_low <= self.floor:
            self._log("rule_breach", rule="MLL", ts=ts, equity_low=eq_low, floor=self.floor)
            self._close_position(ts, self.floor_px(worst_px), "MLL_LIQUIDATION")
            self.status = "FAILED_MLL"
        elif self.cfg.dll is not None and (self.day_pnl + unreal) <= -self.cfg.dll:
            self._log("rule_breach", rule="DLL", ts=ts)
            self._close_position(ts, worst_px, "DLL_LIQUIDATION")
            self.halted_today = True

    def floor_px(self, worst_px):
        return worst_px

    def _end_of_day(self, date):
        self.best_day = max(self.best_day, self.day_pnl)
        prof = self.balance - self.cfg.start_balance
        need = max(self.cfg.target, self.best_day / self.cfg.consistency if self.cfg.consistency else 0)
        if self.status == "ACTIVE" and prof >= need:
            self.status = "PASSED"
        if self.balance > self.eod_high:
            self.eod_high = self.balance
            nf = self.eod_high - self.cfg.mll
            if self.cfg.lock_at_start:
                nf = min(nf, self.cfg.start_balance)
            self.floor = max(self.floor, nf)
        rec = {"date": str(date), "day_pnl": self.day_pnl, "balance": self.balance, "floor": self.floor,
               "best_day": self.best_day, "profit": prof, "target_needed": need, "status": self.status,
               "trades_total": len(self.trades)}
        self.days.append(rec)
        self._log("day", **rec)
        self._monitor()
        self.day_pnl = 0.0
        self.halted_today = False

    def _monitor(self):
        n = len(self.trades)
        if n == 0:
            return
        cum = sum(t["pnl_usd"] / max(t["qty"], 1) for t in self.trades)
        z = (cum - n * self.cfg.exp_trade_mean) / (self.cfg.exp_trade_sd * math.sqrt(n))
        self._log("monitor", trades=n, cum_pnl_per_contract=cum, z_vs_backtest=z)
        if n >= self.cfg.kill_min_trades and z < self.cfg.kill_z and not self.kill:
            self.kill = True
            self._log("KILL_SWITCH", reason=f"cumulative P&L z={z:.2f} below {self.cfg.kill_z} after {n} trades",
                      action="stop paper trading; do NOT buy evaluations; re-research")

    # ------------------------------------------------------------------ main event
    def on_bar(self, ts: pd.Timestamp, o: float, h: float, l: float, c: float, v: float = 0.0):
        """Process one COMPLETED bar (ts = bar open time, UTC)."""
        self.bars.loc[ts] = [o, h, l, c, v]
        e = ts.tz_convert(ET)
        et_min = e.hour * 60 + e.minute
        date = e.normalize().tz_localize(None)
        if self.cur_date is not None and date != self.cur_date and (self.days == [] or self.days[-1]["date"] != str(self.cur_date)):
            pass
        bm = self.cfg.bar_minutes
        # (1) executions inside this bar for orders placed at the previous bar's close
        exited = False
        if self.pending_exit and self.pos != 0:
            self._close_position(ts, o - self._slip() * self.pos, "SIGNAL")
            exited = True
        self.pending_exit = False
        entered_now = False
        if self.pending_entry is not None and self.pos == 0 and not exited and self.status == "ACTIVE" and not self.halted_today:
            pe = self.pending_entry
            self.pos, self.qty = pe["dir"], pe["qty"]
            self.entry_px = o + self._slip() * self.pos
            self.entry_ts = ts
            self.stop = self.entry_px - self.pos * pe["stop_dist"] if np.isfinite(pe["stop_dist"]) else math.nan
            self.mae = 0.0
            self.trades_today += 1
            entered_now = True
            self._log("fill", ts=ts, side="BUY" if self.pos > 0 else "SELL", qty=self.qty, px=self.entry_px,
                      signal_ts=pe["signal_ts"], stop=self.stop)
        self.pending_entry = None
        if self.pos != 0:
            worst = l if self.pos > 0 else h
            self.mae = min(self.mae, (worst - self.entry_px) * self.pos)
            hit = (self.pos > 0 and l <= self.stop) or (self.pos < 0 and h >= self.stop)
            if np.isfinite(self.stop) and hit:
                px = (min(self.stop, o) - self._slip()) if self.pos > 0 else (max(self.stop, o) + self._slip())
                self._close_position(ts, px, "STOP")
            else:
                self._check_realtime_rules(ts, worst)
        # (2) signals at the close of this bar using only data received so far
        hist = self.bars[self.bars.index >= ts - pd.Timedelta(days=self.cfg.history_days)]
        is_check = (et_min + bm) % self.cfg.params.get("check_min", 60) == 0
        flat_now = False
        if et_min + bm >= 16 * 60 and et_min < 16 * 60:
            flat_now = True   # last RTH bar: 15:45-16:00 -> flat at its close (Topstep cut-off 16:10 ET)
        if (is_check or flat_now) and len(hist) > 200:
            ctx = SI.build_context(hist, bm)
            ords = SI.noise_area(ctx, self.cfg.params)
            i = len(ctx) - 1
            # NOTE: the backtester's flat_rth flag cannot be used live (it knows whether later bars exist);
            # the paper trader flattens on the clock (15:45-16:00 ET bar), which is what a live system does.
            if not flat_now:
                if self.pos != 0 and (ords.exit_sig[i] == 2 or ords.exit_sig[i] == self.pos):
                    self.pending_exit = True
                    self._log("signal", ts=ts, action="EXIT", signal_close_time=ts + pd.Timedelta(minutes=bm))
                if (self.pos == 0 and ords.entry_dir[i] != 0 and self.trades_today < self.cfg.params.get("max_trades", 6)
                        and self.status == "ACTIVE" and not self.halted_today and not self.kill):
                    sd = ords.risk_ref[i]
                    if self.cfg.risk_budget_per_sd is None or not np.isfinite(sd):
                        q = self.cfg.fixed_contracts
                    else:
                        q = int(min(max(1, math.floor(self.cfg.risk_budget_per_sd / (sd * self.inst.point_value))),
                                    self.cfg.max_contracts))
                    self.pending_entry = {"dir": int(ords.entry_dir[i]), "qty": q, "stop_dist": float(ords.stop_dist[i]),
                                          "signal_ts": ts}
                    self._log("signal", ts=ts, action="ENTER", dir=int(ords.entry_dir[i]), qty=q,
                              signal_close_time=ts + pd.Timedelta(minutes=bm))
        if flat_now:
            if self.pos != 0:
                self._close_position(ts, c - self._slip() * self.pos, "FLAT_EOD")
            self.pending_entry = None
            self.pending_exit = False
            if self.cur_date != date:
                self.cur_date = date
            self._end_of_day(date)
            self.trades_today = 0

    def summary(self) -> dict:
        t = pd.DataFrame(self.trades)
        return {"status": self.status, "balance": self.balance, "profit": self.balance - self.cfg.start_balance,
                "trades": len(t), "win_rate": float((t.pnl_usd > 0).mean()) if len(t) else None,
                "floor": self.floor, "best_day": self.best_day, "kill_switch": self.kill, "log": str(self.log_path)}


def replay(df: pd.DataFrame, cfg: PaperConfig, log_dir: Path) -> PaperTrader:
    pt = PaperTrader(cfg, log_dir)
    for ts, r in df.iterrows():
        pt.on_bar(ts, r.open, r.high, r.low, r.close, r.get("volume", 0.0))
    return pt
