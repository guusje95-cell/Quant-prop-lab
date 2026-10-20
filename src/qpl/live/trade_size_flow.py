"""Gen248 data: taker flow by TRADE SIZE for the BTC and ETH perps (Binance public archive data.binance.vision, no account, no key).

    python -m qpl.live.trade_size_flow              # BTC + ETH, 2020-01 .. last full month (resumable, several hours, big downloads)
    python -m qpl.live.trade_size_flow BTC          # one coin

For each month it downloads the aggTrades zip (BTC: up to ~2-3 GB per month), streams it in chunks, keeps per UTC hour the taker
buy and sell notional (USD) in four trade-size buckets (< $10k, $10k-100k, $100k-1M, >= $1M) plus trade counts, then deletes the
zip. Output (small): research_data/trade_size/<COIN>USDT_<YYYY-MM>.parquet. Needs ~5 GB free disk while a month is processed."""
import io
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research_data" / "trade_size"
TMP = ROOT / "data" / "tmp_aggtrades"
URL = "https://data.binance.vision/data/futures/um/monthly/aggTrades/{s}/{s}-aggTrades-{m}.zip"
EDGES = [0, 1e4, 1e5, 1e6, np.inf]
NAMES = ["lt10k", "10k_100k", "100k_1m", "ge1m"]
COLS = ["agg_trade_id", "price", "quantity", "first_trade_id", "last_trade_id", "transact_time", "is_buyer_maker"]


def _download(url, f):
    for k in range(5):
        try:
            with requests.get(url, stream=True, timeout=60, headers={"User-Agent": "quant-prop-lab research"}) as r:
                if r.status_code == 404:
                    return False
                if r.status_code in (403, 451):
                    raise RuntimeError(f"Binance archive refused the request ({r.status_code}). Not bypassing it.")
                r.raise_for_status()
                with open(f, "wb") as fh:
                    for chunk in r.iter_content(1 << 22):
                        fh.write(chunk)
            return True
        except RuntimeError:
            raise
        except Exception as e:
            print(f"    download error {e.__class__.__name__}, retry in {30 * (k + 1)} s", flush=True); time.sleep(30 * (k + 1))
    raise RuntimeError(f"giving up on {url}")


def summarize(zpath) -> pd.DataFrame:
    parts = []
    with zipfile.ZipFile(zpath) as z:
        name = z.namelist()[0]
        with z.open(name) as fh:
            head = fh.readline().decode()
        has_header = not head.split(",")[0].strip().isdigit()
        with z.open(name) as fh:
            for ch in pd.read_csv(io.TextIOWrapper(fh), chunksize=5_000_000, header=0 if has_header else None,
                                  names=None if has_header else COLS, usecols=["price", "quantity", "transact_time", "is_buyer_maker"]):
                usd = ch["price"].to_numpy(float) * ch["quantity"].to_numpy(float)
                maker = ch["is_buyer_maker"].astype(str).str.lower().isin(["true", "1"]).to_numpy()
                hour = pd.to_datetime(ch["transact_time"].to_numpy(np.int64), unit="ms").floor("h")
                b = np.digitize(usd, EDGES[1:-1])
                d = pd.DataFrame({"hour": hour, "b": b, "buy": np.where(~maker, usd, 0.0), "sell": np.where(maker, usd, 0.0),
                                  "nbuy": (~maker).astype(np.int64), "nsell": maker.astype(np.int64)})
                parts.append(d.groupby(["hour", "b"]).sum())
    g = pd.concat(parts).groupby(level=[0, 1]).sum().unstack("b").fillna(0.0)
    g.columns = [f"{v}_{NAMES[int(b)]}" for v, b in g.columns]
    return g.astype("float64").sort_index()


def run(coin):
    sym = f"{coin}USDT"; OUT.mkdir(parents=True, exist_ok=True); TMP.mkdir(parents=True, exist_ok=True)
    last_full = (pd.Timestamp.now("UTC").tz_localize(None).normalize().replace(day=1) - pd.Timedelta(days=1)).replace(day=1)
    for m in pd.date_range("2020-01-01", last_full, freq="MS"):
        f = OUT / f"{sym}_{m:%Y-%m}.parquet"
        if f.exists():
            continue
        z = TMP / f"{sym}-{m:%Y-%m}.zip"; t0 = time.time()
        print(f"{sym} {m:%Y-%m}: downloading ...", flush=True)
        if not _download(URL.format(s=sym, m=f"{m:%Y-%m}"), z):
            print(f"{sym} {m:%Y-%m}: not in the archive", flush=True); continue
        g = summarize(z); g.to_parquet(f); z.unlink(missing_ok=True)
        print(f"{sym} {m:%Y-%m}: {len(g)} hours, {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    for c in (sys.argv[1:] or ["BTC", "ETH"]):
        run(c)
