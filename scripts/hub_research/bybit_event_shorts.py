"""v9.9 R2 / hub agenda item 'bybit_event_shorts' (research/v99/r2_protocol.json): Bybit delisting announcements as event shorts,
added to the v9.8 event short with the Binance spot-delisting rule. Needs research_data/bybit_announcements/announcements.json
(get_bybit_announcements.bat on the user's PC). Writes results/hub_research/bybit_event_shorts.json.
`--selftest FILE` runs the pipeline on a hand-made announcements file (code check only, no result is recorded)."""
import gzip
import io
import json
import os
import re
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import requests
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import event_live as EL
END = "2026-09-30"
ANN = ROOT / "research_data/bybit_announcements/announcements.json"
CACHE = ROOT / "hub_data/bybit_trades_1h"; CACHE.mkdir(parents=True, exist_ok=True)
SKIP = re.compile(r"option|margin|copy ?trad|earn|savings|launchpool|launchpad|convert|loan|bot", re.I)
TOK = re.compile(r"\b(?:\d{0,8})?([A-Z][A-Z0-9]{1,14})(?:/USDT|USDT|PERP)\b")


def events(path: Path) -> dict[str, list[tuple[str, pd.Timestamp]]]:
    rows = json.loads(path.read_text()).get("delistings", [])
    out = {"A": [], "B": []}
    for a in rows:
        title = a.get("title") or ""
        if SKIP.search(title):
            continue
        ms = a.get("publishTime") or a.get("dateTimestamp")
        if not ms:
            continue
        t = pd.to_datetime(int(ms), unit="ms")
        if t < pd.Timestamp("2021-06-01") or t > pd.Timestamp(END):
            continue
        coins = sorted({m.group(1) for m in TOK.finditer(title.upper())} - {"USDT", "USDC"})
        kind = "A" if re.search(r"spot", title, re.I) else "B" if re.search(r"perpetual|contract|futures", title, re.I) else None
        if kind:
            out[kind] += [(c, t) for c in coins]
    return out


def bybit_closes(coin: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.Series | None:
    """hourly last-trade closes of <coin>USDT from public.bybit.com daily trade files (cached per coin and day)."""
    parts = []
    for day in pd.date_range(start.normalize(), end.normalize(), freq="D"):
        f = CACHE / f"{coin}_{day:%Y-%m-%d}.parquet"
        if not f.exists():
            r = requests.get(f"https://public.bybit.com/trading/{coin}USDT/{coin}USDT{day:%Y-%m-%d}.csv.gz", timeout=120)
            if r.status_code != 200:
                pd.Series(dtype=float).to_frame("close").to_parquet(f); continue
            d = pd.read_csv(io.BytesIO(gzip.decompress(r.content)), usecols=["timestamp", "price"])
            s = pd.Series(d.price.to_numpy(), index=pd.to_datetime(d.timestamp, unit="s")).sort_index()
            s.resample("1h", label="left").last().dropna().to_frame("close").to_parquet(f)
        x = pd.read_parquet(f)["close"]
        if len(x):
            parts.append(x)
    if not parts:
        return None
    c = pd.concat(parts).sort_index(); c.index = (c.index + pd.Timedelta(hours=1)).as_unit("ns")   # close of hour h stamped at h+1 (bar close)
    return c[~c.index.duplicated(keep="last")]


def make_hook(evts, index):
    def hook(P, CF):
        P = P.copy(); added = 0
        for coin, t in sorted(evts, key=lambda e: e[1]):
            n = "spo_" + coin
            start = t.ceil("h") + pd.Timedelta(hours=1); end = start + pd.Timedelta(days=EL.HOLD)
            if n in P.columns and (P[n].loc[t.floor("h"):end] != 0).any():
                continue                                                 # already shorted for a Binance delisting
            cl, fu = EL._closes(coin)
            if cl is None or not ((cl.index >= t.floor("h") - pd.Timedelta(hours=2)) & (cl.index <= t.ceil("h"))).any():
                cl = bybit_closes(coin, t - pd.Timedelta(days=1), end); fu = pd.Series(dtype=float, index=pd.DatetimeIndex([], dtype="datetime64[ns]"))
            if cl is None or not ((cl.index >= t.floor("h") - pd.Timedelta(hours=3)) & (cl.index <= t.ceil("h") + pd.Timedelta(hours=1))).any():
                continue                                                 # not trading at the announcement
            cc = cl.loc[start:end]
            if len(cc) == 0:
                continue
            hit = cc[cc >= cc.iloc[0] * (1 + EL.STOP)].index; last = hit[0] if len(hit) else min(end, cl.index.max())
            p = pd.Series(-EL.SIZE, index=cl.loc[start:last].index); p.index = p.index + pd.Timedelta(hours=1); p = p.reindex(index).fillna(0.0)
            p = p.where(cl.reindex(index - pd.Timedelta(hours=1)).notna().to_numpy(), 0.0)
            cur = P[n] if n in P.columns else pd.Series(0.0, index=index)
            P[n] = cur.where(cur != 0, p); CF[n] = (cl, fu); added += 1
        hook.added = added
        return P
    return hook


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    dd = lambda h: h.groupby(h.index.floor("D")).sum()
    unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(h, a="2022", z=END):
        d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
    per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
    selftest = "--selftest" in sys.argv
    path = Path(sys.argv[sys.argv.index("--selftest") + 1]) if selftest else ANN
    if not path.exists():
        sys.exit(f"{path} not found: run get_bybit_announcements.bat on the PC first")
    E = events(path)
    s0, _, _ = EL.pnl(idx); b0 = unit(CS.portfolio_v5(V7.assign(**{"listing short": s0}))[0]); ref = [shp(b0), per(b0)]
    out = {"reference_v98": ref, "events": {k: len(v) for k, v in E.items()}, "variants": {}}
    for name, ev in (("A spot", E["A"]), ("B perp", E["B"]), ("A+B", E["A"] + E["B"])):
        h = make_hook(ev, idx); s, _, _ = EL.pnl(idx, pre_cap=h)
        b = unit(CS.portfolio_v5(V7.assign(**{"listing short": s}))[0]); r = [shp(b), per(b)]
        out["variants"][name] = {"events used": getattr(h, "added", 0), "event short": per(s), "book": r,
                                 "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))}
        print(name, out["variants"][name], flush=True)
    out["candidate"] = out["variants"]["A+B"]["book"]; out["pass"] = out["variants"]["A+B"]["pass"]
    if selftest:
        print("SELFTEST ONLY (hand-made events): nothing recorded"); return
    d = Path(os.environ.get("QPL_AGENT_OUT", ROOT / "results/hub_research")); d.mkdir(parents=True, exist_ok=True)   # hub agent: hub_data/agent_results
    p = d / "bybit_event_shorts.json"; p.write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
