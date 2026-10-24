"""Account-level guards: daily stop, kill switch, stale book."""
from __future__ import annotations
from pathlib import Path
import pandas as pd


def day_key(ts: pd.Timestamp) -> str:
    return ts.tz_convert("UTC").strftime("%Y-%m-%d") if ts.tzinfo else ts.strftime("%Y-%m-%d")


class Guard:
    def __init__(self, rules, state: dict, kill_file: Path):
        self.r, self.s, self.kill = rules, state, kill_file

    def new_day(self, now: pd.Timestamp, equity: float):
        k = day_key(now)
        if self.s.get("day") != k:
            self.s.update(day=k, day_start_equity=equity, stopped=False)

    def daily_stop_hit(self, equity: float) -> bool:
        lvl = self.s["day_start_equity"] - self.r.daily_stop_frac * self.r.initial_balance
        if equity <= lvl:
            self.s["stopped"] = True
        return bool(self.s.get("stopped"))

    def killed(self) -> bool:
        return self.kill.exists()

    def book_stale(self, book: dict, now: pd.Timestamp) -> bool:
        made = pd.Timestamp(book["made_at_utc"]); now = now.tz_localize(None) if now.tzinfo else now
        return (now - made).total_seconds() / 60 > self.r.max_book_age_minutes
