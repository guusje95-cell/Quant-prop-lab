"""Free public data, part 2 (no account, no key), saved to research_data/more2/:
  - CFTC Commitments of Traders, weekly since 2010: disaggregated (commodities) and traders-in-financial-futures (indices, rates, FX,
    CME bitcoin/ether) - futures-only reports, the official yearly history files from cftc.gov
  - Deribit option flow, BTC and ETH, hourly since 2020 (history.deribit.com public API, up to 1000 trades per hour): put/call and
    buy/sell volume and the implied-vol skew (OTM puts vs OTM calls, 7-60 day expiries), summarised on your PC (small files)

    python -m qpl.live.free_data2            # everything (resumable; COT ~2 minutes, Deribit several hours)
    python -m qpl.live.free_data2 cot        # one part: cot | deribit
Requests are paced well under the public rate limits."""
import io
import json
import sys
import time
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research_data" / "more2"
HDR = {"User-Agent": "quant-prop-lab research"}


def fetch(url, tries=5):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=60) as r:
                return r.read()
        except Exception as ex:
            err = ex; time.sleep(2 ** (k + 1))
    raise RuntimeError(f"{url}: {err}")


def cot():
    OUT.mkdir(parents=True, exist_ok=True)
    for kind, tag in (("fut_disagg_txt", "disagg"), ("fut_fin_txt", "tff")):
        parts = []
        for y in range(2010, datetime.now(timezone.utc).year + 1):
            z = zipfile.ZipFile(io.BytesIO(fetch(f"https://www.cftc.gov/files/dea/history/{kind}_{y}.zip")))
            parts.append(pd.read_csv(z.open(z.namelist()[0]), low_memory=False)); print(f"COT {tag} {y}: {len(parts[-1])} rows", flush=True)
            time.sleep(1)
        d = pd.concat(parts)
        d.columns = [c.strip() for c in d.columns]
        for c in d.columns:                                # CFTC files mix numbers and space-padded text across years
            if not pd.api.types.is_numeric_dtype(d[c]):
                t = d[c].astype(str).str.strip(); num = pd.to_numeric(t, errors="coerce")
                filled = t.notna() & ~t.isin(["", "nan", "None", "<NA>", "NaN", "."])
                d[c] = num if num.notna().sum() >= 0.99 * filled.sum() else t
        d.to_parquet(OUT / f"cot_{tag}.parquet", index=False); print(f"-> cot_{tag}.parquet {len(d)} rows", flush=True)


MON = {m: i for i, m in enumerate(["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}


def _expiry(code):
    return datetime(2000 + int(code[-2:]), MON[code[-5:-2]], int(code[:-5]), 8, tzinfo=timezone.utc)


def _hour_features(trades, t):
    """One row per hour from up to 1000 option trades: counts, put/call and buy/sell volume, implied-vol skew (7-60 day expiries)."""
    r = {"time": t.replace(tzinfo=None), "n": len(trades)}
    rows = []
    for tr in trades:
        try:
            _, exp, k, cp = tr["instrument_name"].split("-")
            dte = (_expiry(exp) - datetime.fromtimestamp(tr["timestamp"] / 1000, timezone.utc)).total_seconds() / 86400
            rows.append((cp, float(k) / tr["index_price"], dte, tr["iv"], tr["amount"], 1 if tr["direction"] == "buy" else -1))
        except Exception:
            continue
    if not rows:
        return r
    d = pd.DataFrame(rows, columns=["cp", "mny", "dte", "iv", "amt", "side"])
    for cp in ("P", "C"):
        x = d[d.cp == cp]; r[f"vol_{cp}"] = x.amt.sum(); r[f"net_buy_{cp}"] = (x.amt * x.side).sum()
    w = d[(d.dte >= 7) & (d.dte <= 60)]
    pick = lambda m: w[m].iv.median() if m.any() else None
    r["iv_put_otm"] = pick((w.cp == "P") & w.mny.between(0.85, 0.95))
    r["iv_call_otm"] = pick((w.cp == "C") & w.mny.between(1.05, 1.15))
    r["iv_atm"] = pick(w.mny.between(0.97, 1.03))
    return r


def deribit(currency, start=datetime(2020, 1, 1, tzinfo=timezone.utc)):
    """Hourly option-flow features per month file (only completed months; run again later to add new ones)."""
    OUT.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    m = start
    while True:
        nxt = (m.replace(day=1) + timedelta(days=32)).replace(day=1)
        if nxt > now:
            break
        f = OUT / f"deribit_{currency}_optflow_{m:%Y-%m}.parquet"
        if not f.exists():
            rows, t = [], m
            while t < nxt:
                a = int(t.timestamp() * 1000); b = int((t + timedelta(hours=1)).timestamp() * 1000)
                url = ("https://history.deribit.com/api/v2/public/get_last_trades_by_currency_and_time?"
                       f"currency={currency}&kind=option&start_timestamp={a}&end_timestamp={b}&count=1000&sorting=asc")
                rows.append(_hour_features(json.loads(fetch(url))["result"]["trades"], t))
                t += timedelta(hours=1); time.sleep(0.25)
            pd.DataFrame(rows).to_parquet(f, index=False); print(f"Deribit {currency} {m:%Y-%m}: {len(rows)} hours", flush=True)
        m = nxt


if __name__ == "__main__":
    from qpl.live.keepawake import keep_awake
    keep_awake()
    part = sys.argv[1] if len(sys.argv) > 1 else "all"
    if part in ("cot", "all"):
        cot()
    if part in ("deribit", "all"):
        for c in ("BTC", "ETH"):
            deribit(c)
    print("Done.")
