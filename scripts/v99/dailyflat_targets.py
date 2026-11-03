"""Target book of the daily-flat equity-index book (DF-3 / DF-4) for the next or current session, from the futures data
(research + Databento top-ups), for a DRY-RUN bot on index CFDs (US500 / US100 / US2000 / US30) or micro futures.

Session d runs from 18:00 ET of the previous trading day to 16:00 ET of d (the bot is flat 15:55-18:00 ET and at weekends).
  - run after the 16:00 ET close (e.g. 16:30 ET): targets for the NEXT session ('before 14:00' part; R1 'after 14:00' not yet known)
  - run after 14:00 ET of d (e.g. 14:05 ET): adds the 'after 14:00' targets of the running session (R1 switch)
Targets are fractions of equity per market at book risk 1 (the book's 10% vol target); the account multiplies by its own risk.
The next session's calendar days are made known by appending one placeholder bar (return 0) at its 18:00 ET open.

    python scripts/v99/dailyflat_targets.py            # writes paper_trading/futuresdf/targets_session.json"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "scripts/v99")); sys.path.insert(0, str(ROOT / "src"))
OUT = Path(os.environ.get("QPL_DF_TARGETS", ROOT / "paper_trading/futuresdf/targets_session.json"))
CFD = {"ES": "US500", "NQ": "US100", "RTY": "US2000", "YM": "US30"}
RESEARCH_END = pd.Timestamp("2026-09-30")


def _setup(now_utc: pd.Timestamp):
    if "QPL_DATABENTO" not in os.environ and "--research" not in sys.argv:
        try:
            from qpl.live import databento_update as DU
            os.environ["QPL_DATABENTO"] = str(DU.merged_dir())
        except Exception:                                                    # noqa: BLE001 - research data only
            pass
    import dailyflat
    F = dailyflat.patch()
    F.END = str(now_utc.floor("h"))
    return F


def next_session(now_et: pd.Timestamp) -> pd.Timestamp:
    """the session (trading date) a bot should hold at / after now (ET, naive)"""
    d = now_et.normalize()
    if now_et.hour >= 16:
        d += pd.Timedelta(days=1)
    while d.weekday() >= 5:
        d += pd.Timedelta(days=1)
    return d


def _placeholder(F, session: pd.Timestamp, days_ahead: int = 45):
    """append placeholder bars (return 0) at the 18:00 ET open of `session` and of the following trading days (US federal holidays
    skipped): calendar sleeves need the future trading calendar (month starts, pre-holiday days, FOMC weeks, the last days of a month),
    which is known in advance; price-based signals only use bars up to now"""
    from functools import lru_cache
    from pandas.tseries.holiday import USFederalHolidayCalendar
    days = pd.date_range(session, session + pd.Timedelta(days=days_ahead), freq=pd.offsets.CustomBusinessDay(calendar=USFederalHolidayCalendar()))
    days = days.union(pd.DatetimeIndex([session]))
    opens = pd.DatetimeIndex([pd.Timestamp(d - pd.Timedelta(days=1) + pd.Timedelta(hours=18)).tz_localize("America/New_York").tz_convert("UTC").tz_localize(None)
                              for d in days])                              # the session opens at 18:00 ET the calendar day before
    for name in ("front", "second"):
        cached = getattr(F, name)

        def wrap(root, _c=cached):
            f = _c(root); add = opens[opens > f.index[-1]]
            if not len(add):
                return f
            rows = pd.concat([f.iloc[[-1]]] * len(add)); rows.index = add; rows["r"] = 0.0
            if "roll" in rows:
                rows["roll"] = 0
            if "open" in rows:
                rows["open"] = rows["close"]
            return pd.concat([f, rows])
        setattr(F, name, lru_cache(maxsize=None)(wrap))


def build(now_utc: pd.Timestamp | None = None, write: bool = True) -> dict:
    now_utc = pd.Timestamp.now(tz="UTC") if now_utc is None else pd.Timestamp(now_utc)
    if now_utc.tzinfo:
        now_utc = now_utc.tz_convert("UTC").tz_localize(None)
    F = _setup(now_utc)
    now_et = now_utc.tz_localize("UTC").tz_convert("America/New_York").tz_localize(None)
    session = next_session(now_et)
    _placeholder(F, session)
    import fbook  # noqa: F401
    import dailyflat_positions as DP
    pos = DP.session_positions()
    EQ = DP.EQ8
    # book weights: fbook rule on the research sleeves (fixed: fit 2010-22)
    Q = pd.read_parquet(ROOT / "results/v99/df1_sleeves.parquet")[EQ]; Q = Q[Q.index.weekday < 5].loc["2010-06-01":RESEARCH_END].fillna(0.0)
    T = Q.loc[:"2022-12-31"]; w = (1 / T.std()).where(T.mean() / T.std() > 0, 0.0); w = w / w.sum()
    # daily sleeve P&L after the research end: positions x patched bars - own turnover x cost (as DF-4, per sleeve)
    H = DP.hourly(pos); live = {}
    for n in EQ:
        tot = 0.0
        for r in H[n].columns:
            f = F.front(r); idx = f.index; et = F.ny(idx); p = H[n][r].reindex(idx).fillna(0.0).copy(); p[(et.h == 16).to_numpy()] = 0.0
            tot = tot + (p * f.r.fillna(0.0) - p.diff().abs().fillna(p.abs()) * F.cost_frac(r, f.close)).groupby(F.trade_date(idx)).sum()
        live[n] = tot
    L = pd.DataFrame(live); L = L[(L.index > RESEARCH_END) & (L.index < session) & (L.index.weekday < 5)]
    S = pd.concat([Q, L]).fillna(0.0); S = S[S.index < session]                    # point in time: only sessions before this one
    raw = (S * w).sum(axis=1); vol = raw.rolling(60, min_periods=40).std().iloc[-1] * np.sqrt(252)
    lvl = float(min(3.0, 0.10 / vol)) if vol > 0 else 0.0
    def tgt(key_r1):
        out = {}
        for r in DP.MK4:
            v = 0.0
            for n in EQ:
                P = pos["R1 until 14:00" if (n == "R1" and key_r1 == "before") else "R1 from 14:00"] if n == "R1" else pos[n]
                if r in P and session in P.index:
                    v += w[n] * lvl * float(P.loc[session, r])
            out[CFD[r]] = round(v, 6)
        return out
    after_known = session in pos["R1 from 14:00"].index and now_et >= session + pd.Timedelta(hours=14)
    res = {"session": str(session.date()), "made_at_utc": str(now_utc.floor("s")), "level": round(lvl, 4),
           "weights": {k: round(float(v), 4) for k, v in w.items()},
           "targets_before_14et": tgt("before"), "targets_after_14et": tgt("after") if after_known else None,
           "markets": CFD, "units": "fraction of equity at book risk 1 (10% vol target); account notional = fraction x equity x account risk",
           "schedule_et": {"flat": "15:55-18:00 and Fri 15:55 -> Sun 18:00", "enter": "18:00 open (or the first bar after)", "r1_switch": "14:00"},
           "note": "DRY-RUN target book (DF-3 / DF-4); not a paper account; no order is sent"}
    if write:
        OUT.parent.mkdir(parents=True, exist_ok=True); tmp = OUT.with_suffix(".tmp"); tmp.write_text(json.dumps(res, indent=1)); tmp.replace(OUT)
    return res


if __name__ == "__main__":
    t = None
    for a in sys.argv[1:]:
        if a.startswith("--at="):
            t = pd.Timestamp(a[5:])
    print(json.dumps(build(t, write="--no-write" not in sys.argv), indent=1))
