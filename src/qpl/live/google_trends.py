"""Gen265 data: daily Google search interest (retail attention, Koch & Dimpfl 2022) for crypto terms, 2020-01 .. today.
Free (Google Trends via the pytrends package, no account); run on your own PC. Google limits requests, so this pauses between
calls and resumes where it stopped.

    pip install pytrends
    python -m qpl.live.google_trends

Daily values only exist for windows up to ~270 days; windows overlap by 60 days and are chained (each window rescaled to the
previous one on the overlap), the standard stitching method. Output: research_data/attention/google_<term>_1d.parquet"""
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research_data" / "attention"
TERMS = ["bitcoin", "ethereum", "crypto", "buy bitcoin", "solana", "xrp", "dogecoin"]


def windows(start="2020-01-01", span=260, overlap=60):
    t0 = pd.Timestamp(start); end = pd.Timestamp.now().normalize(); out = []
    while t0 < end:
        t1 = min(t0 + pd.Timedelta(days=span), end); out.append((t0, t1))
        if t1 >= end:
            break
        t0 = t1 - pd.Timedelta(days=overlap)
    return out


def fetch(term):
    from pytrends.request import TrendReq
    OUT.mkdir(parents=True, exist_ok=True); cache = OUT / f"_raw_{term.replace(' ', '_')}"; cache.mkdir(exist_ok=True)
    py = TrendReq(hl="en-US", tz=0, timeout=(10, 30))
    parts = []
    for a, b in windows():
        f = cache / f"{a:%Y%m%d}_{b:%Y%m%d}.parquet"
        if not f.exists():
            for k in range(5):
                try:
                    py.build_payload([term], timeframe=f"{a:%Y-%m-%d} {b:%Y-%m-%d}")
                    d = py.interest_over_time()
                    if d.empty:
                        raise RuntimeError("empty")
                    d[[term]].astype(float).to_parquet(f); break
                except Exception as e:
                    wait = 60 * (k + 1); print(f"  {term} {a.date()}: {e.__class__.__name__}, waiting {wait} s", flush=True); time.sleep(wait)
            else:
                print(f"  {term}: giving up for now (run again later; it resumes)", flush=True); return None
            time.sleep(8)
        parts.append(pd.read_parquet(f)[term])
    s = parts[0]
    for p in parts[1:]:                                                # chain: rescale each window to the previous on the overlap
        ov = s.index.intersection(p.index); ov = ov[(s.loc[ov] > 0) & (p.loc[ov] > 0)]
        k = (s.loc[ov].mean() / p.loc[ov].mean()) if len(ov) else 1.0
        s = pd.concat([s, p[p.index > s.index.max()] * k])
    s = s / s.max() * 100; f = OUT / f"google_{term.replace(' ', '_')}_1d.parquet"
    s.to_frame("interest").to_parquet(f); print(f"{term}: {len(s)} days {s.index.min().date()} .. {s.index.max().date()} -> {f}", flush=True)
    return s


if __name__ == "__main__":
    for t in (sys.argv[1:] or TERMS):
        fetch(t)
