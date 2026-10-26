"""Gen431 data: Bybit USDT linear perps - launch time, first 40 days of hourly klines and funding (public v5 market API, no key).
Run on a PC where Bybit is reachable (it blocks some cloud regions; do not route around it):   get_bybit_listings.bat
Writes research_data/bybit_listings/instruments.json and <SYM>_1h.parquet / <SYM>_funding.parquet."""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research_data" / "bybit_listings"
B = "https://api.bybit.com/v5/market"
UA = {"User-Agent": "Mozilla/5.0 (research; quant-prop-lab)"}


def get(path: str, **params):
    url = f"{B}/{path}?" + urllib.parse.urlencode(params)
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                j = json.loads(r.read().decode())
            if j.get("retCode") == 0:
                time.sleep(0.12); return j["result"]
            if j.get("retCode") in (10006, 10018):                    # rate limit: back off
                time.sleep(5 * (i + 1)); continue
            raise RuntimeError(j)
        except Exception as e:                                       # noqa: BLE001
            if i == 4:
                raise
            print(f"  retry {i + 1}: {e}"); time.sleep(2 ** (i + 1))


def instruments() -> list[dict]:
    rows = []
    for status in ("Trading", "Closed", "Delivering", "PreLaunch"):
        cursor = ""
        while True:
            try:
                r = get("instruments-info", category="linear", status=status, limit=1000, cursor=cursor)
            except Exception as e:                                   # noqa: BLE001 - a status Bybit does not serve: skip it
                print(f"  status {status}: {e}"); break
            rows += [x for x in r.get("list", []) if x.get("quoteCoin") == "USDT" and x.get("contractType") == "LinearPerpetual"]
            cursor = r.get("nextPageCursor") or ""
            if not cursor:
                break
    seen = {}
    for x in rows:
        seen[x["symbol"]] = {"symbol": x["symbol"], "status": x.get("status"), "launchTime": int(x.get("launchTime") or 0),
                             "fundingInterval": x.get("fundingInterval")}
    return sorted(seen.values(), key=lambda d: d["launchTime"])


def one(sym: str, launch_ms: int, days: int = 40):
    end_ms = launch_ms + days * 86400_000
    k = get("kline", category="linear", symbol=sym, interval="60", start=launch_ms, end=end_ms, limit=1000).get("list", [])
    if k:
        d = pd.DataFrame(k, columns=["t", "open", "high", "low", "close", "volume", "turnover"]).astype(float)
        d.index = pd.to_datetime(d.pop("t").astype("int64"), unit="ms"); d.index.name = "time"
        d.sort_index()[["close", "turnover"]].rename(columns={"turnover": "quote_volume"}).to_parquet(OUT / f"{sym}_1h.parquet")
    rows, e = [], end_ms
    for _ in range(20):
        f = get("funding/history", category="linear", symbol=sym, startTime=launch_ms, endTime=e, limit=200).get("list", [])
        if not f:
            break
        rows += f; e = int(f[-1]["fundingRateTimestamp"]) - 1
        if len(f) < 200:
            break
    if rows:
        d = pd.DataFrame({"time": pd.to_datetime([int(x["fundingRateTimestamp"]) for x in rows], unit="ms"), "last_funding_rate": [float(x["fundingRate"]) for x in rows]})
        d.drop_duplicates("time").sort_values("time").to_parquet(OUT / f"{sym}_funding.parquet", index=False)


def main(first="2021-06-01"):
    OUT.mkdir(parents=True, exist_ok=True)
    ins = instruments(); (OUT / "instruments.json").write_text(json.dumps(ins, indent=1))
    todo = [x for x in ins if x["launchTime"] >= pd.Timestamp(first).value // 1_000_000]
    print(f"{len(ins)} USDT perps, {len(todo)} launched since {first}", flush=True)
    for i, x in enumerate(todo):
        if (OUT / f"{x['symbol']}_1h.parquet").exists():
            continue
        try:
            one(x["symbol"], x["launchTime"])
        except Exception as e:                                       # noqa: BLE001
            print(f"  {x['symbol']}: {e}")
        if i % 50 == 0:
            print(f"  {i}/{len(todo)}", flush=True)
    print(f"done -> {OUT} (push it: git add research_data/bybit_listings && git commit -m 'Bybit listings' && git push)")


if __name__ == "__main__":
    main()
