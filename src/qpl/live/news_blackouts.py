"""News blackout list for the MT5 bridge (audit A-3, 2026-11-10): BrightFunded funded accounts must not place orders within 5 minutes of
high-impact ('red-folder') news; qpl.bot.venue_mt5.in_blackout reads config/news_blackouts.json (UTC times, +-6 minutes) but the file
was never created, so the guard was inactive.

Sources: the scheduled FOMC meetings on federalreserve.gov (statement 14:00 ET, press conference 14:30 ET, converted to UTC with New
York daylight saving) for this and next year, plus config/news_manual.json (a JSON list of UTC times or {"et": "YYYY-MM-DD HH:MM"} items)
for other red-folder events, e.g. CPI and payrolls (08:30 ET) from the firm's calendar - BLS blocks scripts. On a network error the old
file is kept.

    python -m qpl.live.news_blackouts"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from qpl.live import fomc_dates as FD

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "config/news_blackouts.json"
MANUAL = ROOT / "config/news_manual.json"


def _et(s: str) -> pd.Timestamp:
    return pd.Timestamp(s).tz_localize("America/New_York").tz_convert("UTC").tz_localize(None)


def fomc_times(html: str) -> list[pd.Timestamp]:
    out = []
    parts = re.split(r"(20\d\d) FOMC Meetings", html)
    for i in range(1, len(parts) - 1, 2):
        y = int(parts[i])
        for d in FD.calendar_meetings(parts[i + 1], y) or FD.meetings(parts[i + 1], y):
            out += [_et(f"{d.date()} 14:00"), _et(f"{d.date()} 14:30")]
    return out


def manual() -> list[pd.Timestamp]:
    if not MANUAL.exists():
        return []
    out = []
    for x in json.loads(MANUAL.read_text()):
        out.append(_et(x["et"]) if isinstance(x, dict) else pd.Timestamp(x))
    return out


def build(now: pd.Timestamp | None = None) -> dict:
    now = now or pd.Timestamp.now(tz="UTC").tz_localize(None)
    try:
        ts = fomc_times(FD.get("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"))
    except Exception as e:                                                    # noqa: BLE001 - keep the old list
        return {"status": f"FOMC calendar not reachable ({e}); kept {OUT.name}"}
    ts = sorted({t for t in ts + manual() if t >= now - pd.Timedelta(days=1)})
    OUT.write_text(json.dumps([str(t) for t in ts], indent=1))
    return {"status": "ok", "events": len(ts), "next": [str(t) for t in ts[:4]]}


if __name__ == "__main__":
    print(json.dumps(build(), indent=1))
