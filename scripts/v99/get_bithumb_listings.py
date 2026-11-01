"""First trading hour of every Bithumb KRW market (public v1 API, no key): page back through daily candles to the first day, then the
first hourly candle of that day -> research_data/bithumb_listings/first_trade.json. Delisted markets are not served."""
import json
import time
from pathlib import Path
import pandas as pd
import requests
ROOT = Path(__file__).resolve().parents[2]; OUT = ROOT / "research_data/bithumb_listings/first_trade.json"; API = "https://api.bithumb.com/v1"


def get(path, params):
    for i in range(5):
        try:
            r = requests.get(API + path, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
        except requests.RequestException:
            pass
        time.sleep(2 ** i)
    return None


def first_day(m):
    to = None; first = None
    for _ in range(20):
        p = {"market": m, "count": 200}
        if to:
            p["to"] = to
        c = get("/candles/days", p); time.sleep(0.12)
        if not c:
            break
        first = min(x["candle_date_time_utc"] for x in c)
        if len(c) < 200:
            break
        to = first.replace("T", " ")
    return first


def main():
    M = [m["market"] for m in get("/market/all", {}) if m["market"].startswith("KRW-")]; out = json.loads(OUT.read_text()) if OUT.exists() else {}
    for m in M:
        if m in out:
            continue
        d = first_day(m)
        if not d:
            continue
        h = get("/candles/minutes/60", {"market": m, "count": 24, "to": (pd.Timestamp(d) + pd.Timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")}); time.sleep(0.12)
        out[m] = {"base": m[4:], "first_trade_utc": (min(x["candle_date_time_utc"] for x in h) if h else d).replace("T", " ")}
        if len(out) % 50 == 0:
            OUT.write_text(json.dumps(out, indent=0)); print(len(out), m, out[m], flush=True)
    OUT.write_text(json.dumps(out, indent=0)); print("done", len(out))


if __name__ == "__main__":
    main()
