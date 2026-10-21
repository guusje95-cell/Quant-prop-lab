"""Live inputs of the v7 'ridge ML' sleeve that the Binance/Coinbase updaters do not cover (public endpoints, no account, no key):
  - Upbit KRW hourly BTC/ETH and Yahoo USD/KRW daily (kimchi premium, Gen105 strict)
  - Deribit DVOL daily BTC/ETH (www.deribit.com public API)
Written to <live>/ml/ in the research file formats; scripts/ridge_live.py overlays them on the research copies.

    python -m qpl.live.ml_feeds paper_trading/v7/data      # normally called by scripts/paper_v5.py run (QPL_PAPER=v7)

Each source re-fetches its last few bars so a bar that was still forming is replaced by its final value."""
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from qpl.live.more_data import get

ROOT = Path(__file__).resolve().parents[3]
MORE = ROOT / "research_data" / "more"


def _last(live: Path, base: Path, name: str):
    for f in (live / name, base / name):
        if f.exists():
            return pd.DatetimeIndex(pd.read_parquet(f).index).max()
    return None


def _save(df: pd.DataFrame, f: Path):
    f.parent.mkdir(parents=True, exist_ok=True)
    if f.exists():
        df = pd.concat([pd.read_parquet(f), df])
    df = df[~df.index.duplicated(keep="last")].sort_index(); df.to_parquet(f)
    return len(df)


def upbit(live: Path, log=print, alts=False):
    mk = ["KRW-BTC", "KRW-ETH"]
    if alts:                                                   # v8: every altcoin with a research Upbit file (Gen247 A)
        mk += sorted(p.stem.replace("upbit_", "").replace("_1h", "") for p in MORE.glob("upbit_KRW-*_1h.parquet")
                     if p.stem not in ("upbit_KRW-BTC_1h", "upbit_KRW-ETH_1h"))
    for m in mk:
        name = f"upbit_{m}_1h.parquet"; last = _last(live, MORE, name)
        stop = (last - pd.Timedelta(hours=3)).to_pydatetime().replace(tzinfo=timezone.utc) if last is not None else \
            datetime.now(timezone.utc) - timedelta(days=60)
        to = datetime.now(timezone.utc).replace(second=0, microsecond=0) + timedelta(hours=1); rows = []
        while to > stop:
            js = get(f"https://api.upbit.com/v1/candles/minutes/60?market={m}&count=200&to={to:%Y-%m-%dT%H:%M:%SZ}")
            if not js:
                break
            rows += js; to = datetime.fromisoformat(js[-1]["candle_date_time_utc"]).replace(tzinfo=timezone.utc); time.sleep(0.25)
        if rows:
            d = pd.DataFrame(rows); d.index = pd.to_datetime(d["candle_date_time_utc"])
            d = d[["opening_price", "high_price", "low_price", "trade_price", "candle_acc_trade_volume"]].astype(float)
            d.columns = ["open", "high", "low", "close", "volume"]
            log(f"  upbit {m}: {_save(d, live / name)} rows, last {d.index.max()}")


def usdkrw(live: Path, log=print):
    js = get(f"https://query1.finance.yahoo.com/v8/finance/chart/KRW=X?period1={int(time.time()) - 40 * 86400}"
             f"&period2={int(time.time())}&interval=1d")["chart"]["result"][0]
    d = pd.DataFrame({"close": js["indicators"]["quote"][0]["close"]}, index=pd.to_datetime(js["timestamp"], unit="s")).dropna()
    log(f"  USD/KRW: {_save(d, live / 'yahoo_USDKRW_1d.parquet')} rows, last {d.index.max()}")


def dvol(live: Path, log=print):
    for c in ("BTC", "ETH"):
        name = f"{c}_DVOL.parquet"; last = _last(live, ROOT / "data/raw/deribit", name)
        start = (last - pd.Timedelta(days=3)) if last is not None else pd.Timestamp.now() - pd.Timedelta(days=60)
        js = get("https://www.deribit.com/api/v2/public/get_volatility_index_data?currency=" + c +
                 f"&start_timestamp={int(start.timestamp() * 1000)}&end_timestamp={int(time.time() * 1000)}&resolution=1D")
        d = pd.DataFrame(js["result"]["data"], columns=["t", "open", "high", "low", "close"])
        d.index = pd.to_datetime(d.pop("t"), unit="ms").astype("datetime64[ms]"); d.index.name = "t"
        log(f"  DVOL {c}: {_save(d.astype(float), live / name)} rows, last {d.index.max()}")


def spot(live: Path, log=print):
    """Binance SPOT hourly BTC/ETH with taker-buy volume (bf2.2 ridge, Gen247 B features), research format, last bars re-fetched."""
    from qpl.live import binance_public as BP
    c = BP.Client(); now = pd.Timestamp.now("UTC").tz_localize(None).floor("h")
    for coin in ("BTC", "ETH"):
        name = f"spot/{coin}USDT_1h.parquet"; last = _last(live, ROOT / "research_data/binance_spot", f"{coin}USDT_1h.parquet")
        if (live / name).exists():
            last = pd.DatetimeIndex(pd.read_parquet(live / name).index).max()
        start = (last - pd.Timedelta(hours=3)) if last is not None else now - pd.Timedelta(days=60)
        k = None
        for host in BP.SPOT:
            try:
                k = BP._klines(c, f"{host}/api/v3/klines", f"{coin}USDT", "1h", start, now, limit=1000); break
            except BP.Restricted:
                raise
            except Exception:
                k = None
        if k is None or not len(k):
            raise RuntimeError(f"spot {coin}: no data")
        k = k[["close", "volume", "quote_volume", "taker_buy_volume", "taker_buy_quote_volume"]].astype("float32")
        log(f"  spot {coin}: {_save(k, live / name)} rows, last {k.index.max()}")


def update(data_dir: Path, log=print, alts=False, spot_flow=False) -> bool:
    """Update every ridge input in <data_dir>/ml (alts=True: also the Upbit altcoins for v8's alt kimchi sleeve;
    spot_flow=True: also Binance spot BTC/ETH for bf2.2's ridge). Returns False if a source failed (the sleeves then use what they have)."""
    live = Path(data_dir) / "ml"; ok = True
    for fn in (upbit, usdkrw, dvol) + ((spot,) if spot_flow else ()):
        try:
            fn(live, log, alts) if fn is upbit else fn(live, log)
        except Exception as e:
            log(f"  {fn.__name__}: not updated ({e.__class__.__name__}: {e})"); ok = False
    return ok


if __name__ == "__main__":
    update(Path(sys.argv[1]) if sys.argv[1:] else ROOT / "paper_trading/v7/data")
