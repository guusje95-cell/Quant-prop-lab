"""v9.9 R1b (research/v99/r1b_protocol.json): R1 limit-order fills re-measured on Bybit trade-by-trade history.

Streams only the first ~75 minutes of each public.bybit.com/trading/<COIN>USDT/<COIN>USDT<date>.csv.gz file (the files are sorted
by time and start at 00:00 UTC), caches them in hub_data/bybit_ticks/, and evaluates every sampled daily-sleeve order with the
r1_limit.py accounting against (a) real Bybit quotes / trade-throughs and (b) the R1 model on Binance 5-minute bars.
Writes results/v99/r1b_ticks.json."""
import io
import json
import sys
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
import pandas as pd
import requests
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import binance_pack as B, extra_pack as X
CACHE = ROOT / "hub_data/bybit_ticks"; CACHE.mkdir(parents=True, exist_ok=True)
N = pd.read_parquet(ROOT / "results/v99/netpos.parquet"); ND = pd.read_parquet(ROOT / "results/v99/netpos_daily.parquet"); ix = N.index
TOP10 = {"SOL", "XRP", "BNB", "DOGE", "ADA", "TRX", "AVAX", "LINK", "TON", "SUI"}; ALT = set(B.coins()) | set(X.coins())
cls = lambda c: "major" if c in ("BTC", "ETH") else "top10" if c in TOP10 else "alt" if c in ALT else "event"
HS = {"major": 0.5, "top10": 1.5, "alt": 3.0, "event": 10.0}
mid = ix[ix.hour == 0]
dN = N.diff().loc[mid]; dD = ND.diff().loc[mid]
X_ = dD.where(np.sign(dD) == np.sign(dN), 0.0); X_ = np.sign(X_) * np.minimum(X_.abs(), dN.abs())
COINS = [c for c in X_.columns if c in B.coins() and X_[c].abs().sum() > 0]
rng = np.random.default_rng(7)
days = X_.loc["2023-01-01":"2026-09-30"].index
DAYS = sorted(pd.DatetimeIndex(rng.choice(days.to_numpy(), size=100, replace=False)))
W_MAX = 75


def ticks(coin, day) -> pd.DataFrame | None:
    f = CACHE / f"{coin}_{day:%Y-%m-%d}.parquet"
    if f.exists():
        return pd.read_parquet(f)
    url = f"https://public.bybit.com/trading/{coin}USDT/{coin}USDT{day:%Y-%m-%d}.csv.gz"
    stop = (day + pd.Timedelta(minutes=W_MAX)).timestamp()
    try:
        r = requests.get(url, stream=True, timeout=60)
        if r.status_code != 200:
            return None
        z = zlib.decompressobj(16 + zlib.MAX_WBITS); buf = b""; rows = []; done = False
        for chunk in r.iter_content(1 << 16):
            buf += z.decompress(chunk)
            *lines, buf = buf.split(b"\n")
            for ln in lines:
                if not ln or ln.startswith(b"timestamp"):
                    continue
                p = ln.split(b",")
                t = float(p[0])
                if t > stop:
                    done = True; break
                rows.append((t, p[2] == b"Buy", float(p[3]), float(p[4])))
            if done:
                break
        r.close()
    except Exception as e:                                                   # noqa: BLE001 - network hiccup: skip this file
        print(f"{coin} {day:%Y-%m-%d}: {e}", flush=True); return None
    d = pd.DataFrame(rows, columns=["t", "buy", "size", "price"]); d.to_parquet(f); return d


def tick_order(T, day, x, d, W):
    """gain in bp (THROUGH and TOUCH) for one order of signed size x on Bybit ticks; None if no quote."""
    t0 = (day + pd.Timedelta(minutes=d)).timestamp(); tW = t0 + W * 60
    q = T[(T.t >= t0 - 60) & (T.t <= t0 + 5)]
    bids, asks = q[~q.buy], q[q.buy]
    if bids.empty or asks.empty:
        return None
    bid0, ask0 = bids.price.iloc[-1], asks.price.iloc[-1]
    w = T[(T.t > t0) & (T.t <= tW)]; e = T[T.t <= tW]
    bW = e[~e.buy].price.iloc[-1]; aW = e[e.buy].price.iloc[-1]; PW = 0.5 * (bW + aW)
    sg = np.sign(x)
    entry0 = ask0 if sg > 0 else bid0; L = bid0 if sg > 0 else ask0; entryW = aW if sg > 0 else bW
    base = sg * (PW / entry0 - 1) - 5.5e-4
    through = (w.price < L).any() if sg > 0 else (w.price > L).any()
    touch = (((~w.buy) & (w.price <= L)).any()) if sg > 0 else ((w.buy & (w.price >= L)).any())
    unf = sg * (PW / entryW - 1) - 5.5e-4
    fil = sg * (PW / L - 1) - 2e-4
    return {"through": ((fil if through else unf) - base) * 1e4, "touch": ((fil if touch else unf) - base) * 1e4,
            "fill_through": bool(through), "fill_touch": bool(touch), "half_spread_bp": (ask0 - bid0) / (ask0 + bid0) * 1e4}


K5 = {}
def model_order(c, day, x, d, W, delta=1.0):
    """r1_limit.py gain (bp) for the same order on Binance 5-min bars."""
    if c not in K5:
        K5[c] = B.k5(c)[["low", "high", "close"]]
    k = K5[c]; hs = HS[cls(c)] / 1e4
    s = day + pd.Timedelta(minutes=d); bars = k.loc[s:s + pd.Timedelta(minutes=W - 5)]; pre = k["close"].loc[:s - pd.Timedelta(minutes=5)]
    if len(bars) == 0 or len(pre) == 0:
        return None
    P0 = pre.iloc[-1]; PW = bars["close"].iloc[-1]; sg = np.sign(x)
    base = sg * (PW / (P0 * (1 + sg * hs)) - 1) - 5.5e-4
    L = P0 * (1 - sg * hs)
    hit = bars["low"] <= L * (1 - delta / 1e4) if sg > 0 else bars["high"] >= L * (1 + delta / 1e4)
    cand = sg * (PW / L - 1) - 2e-4 if hit.any() else -(hs + 5.5e-4)
    return (cand - base) * 1e4


jobs = [(c, day) for day in DAYS for c in COINS if X_.loc[day, c] != 0 and np.isfinite(X_.loc[day, c])]
print(f"{len(DAYS)} days, {len(jobs)} orders to measure", flush=True)
with ThreadPoolExecutor(8) as ex:
    TK = dict(zip(jobs, ex.map(lambda j: ticks(*j), jobs)))
rows = []
for (c, day), T in TK.items():
    if T is None or T.empty:
        continue
    x = float(X_.loc[day, c])
    for d in (0, 10):
        t = tick_order(T, day, x, d, 60); m = model_order(c, day, x, d, 60)
        if t is None or m is None:
            continue
        rows.append({"coin": c, "class": cls(c), "day": str(day.date()), "d": d, "notional": abs(x), "model": m, **t})
R = pd.DataFrame(rows); R.to_parquet(ROOT / "results/v99/r1b_orders.parquet")
def wmean(g, col):
    return float(np.average(g[col], weights=g["notional"]))
out = {"sample days": len(DAYS), "orders measured": int((R.d == 0).sum()), "orders without a Bybit file / quote": len(jobs) - int((R.d == 0).sum())}
for d in (0, 10):
    g = R[R.d == d]
    res = {"mean gain bp (notional-weighted)": {"model (R1)": round(wmean(g, "model"), 2), "Bybit THROUGH": round(wmean(g, "through"), 2), "Bybit TOUCH": round(wmean(g, "touch"), 2)},
           "fill rate": {"THROUGH": round(float(g.fill_through.mean()), 3), "TOUCH": round(float(g.fill_touch.mean()), 3)},
           "median Bybit half spread bp by class": g.groupby("class").half_spread_bp.median().round(2).to_dict(),
           "by class (model / through / touch, bp)": {k: [round(wmean(v, "model"), 2), round(wmean(v, "through"), 2), round(wmean(v, "touch"), 2)] for k, v in g.groupby("class")}}
    ratio = wmean(g, "through") / wmean(g, "model")
    res["tick / model ratio (THROUGH)"] = round(ratio, 3)
    res["implied book uplift (R1 central +0.094 x ratio)"] = round(0.094 * ratio, 3)
    out[f"d = {d} min"] = res
u0 = out["d = 0 min"]["implied book uplift (R1 central +0.094 x ratio)"]; c10 = out["d = 10 min"]["mean gain bp (notional-weighted)"]["Bybit THROUGH"]
out["decision"] = "R1 stays a candidate (forward confirmation with the live logger)" if (u0 >= 0.05 and c10 > 0) else "R1 dropped"
(ROOT / "results/v99/r1b_ticks.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
