"""Scheduled FOMC statement dates 2009..now from federalreserve.gov (public pages) -> research_data/more2/fomc_dates.parquet.
Parses the yearly 'FOMC historical' pages (2009-2020) and the current calendars page (2021+). The statement is released on the last
day of each meeting. Unscheduled meetings/conference calls are dropped. The script prints the count per year so it can be checked
(normally 8 a year).

    python -m qpl.live.fomc_dates"""
import re
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research_data" / "more2"
HDR = {"User-Agent": "Mozilla/5.0 (quant-prop-lab research)"}
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"


def get(url):
    for k in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=60) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as ex:
            err = ex; time.sleep(3 * (k + 1))
    raise RuntimeError(f"{url}: {err}")


def meetings(html, year):
    """'Month DD-DD Meeting' / 'Month/Month DD-DD' headings -> last day of each scheduled meeting."""
    text = re.sub(r"<[^>]+>", " ", html); text = re.sub(r"\s+", " ", text)
    out = []
    for m in re.finditer(rf"({MONTHS})(?:/({MONTHS}))?\s+(\d{{1,2}})(?:-(\d{{1,2}}))?\s*(\*)?\s*(Meeting|FOMC Meeting)", text):
        if "unscheduled" in text[max(0, m.start() - 40):m.end() + 40].lower():
            continue
        mon = m.group(2) or m.group(1); day = int(m.group(4) or m.group(3))
        try:
            out.append(pd.Timestamp(f"{mon} {day} {year}"))
        except ValueError:
            pass
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True); dates = []
    for y in range(2009, 2021):
        d = meetings(get(f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{y}.htm"), y)
        dates += d; print(y, len(set(d)), flush=True); time.sleep(1)
    html = get("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm")
    for block in re.split(r"(\d{4}) FOMC Meetings", html)[1:]:
        pass
    parts = re.split(r"(20\d\d) FOMC Meetings", html)
    for i in range(1, len(parts) - 1, 2):
        y = int(parts[i]); d = meetings(parts[i + 1], y); dates += d; print(y, len(set(d)), flush=True)
    s = pd.Series(sorted(set(dates)), name="statement_date")
    s = s[s <= pd.Timestamp.now().normalize()]
    s.to_frame().to_parquet(OUT / "fomc_dates.parquet", index=False)
    print(f"-> {OUT / 'fomc_dates.parquet'}: {len(s)} statement dates {s.min().date()} .. {s.max().date()}")


if __name__ == "__main__":
    main()
