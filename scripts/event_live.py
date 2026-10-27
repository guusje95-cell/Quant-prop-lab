"""v9.8 candidate event-short sleeve for paper trading (Gen468, FLAGGED post hoc, needs the user's OK). Point-in-time: honours
QPL_CUTOFF and the QPL_LIVE_PACK overlay.

Rule: the v9.7 listing short (scripts/listing_live.py) with each listing sized x clip(L / 1.5, 0.5, 2), L = mean all-account
long/short ratio over the 24 h before its entry (research: config/listing_crowding.json; live: <live>/listings/<SYM>_ratios.parquet,
size 1 when fewer than 51 five-minute rows), plus a short of 0.05 in every coin named in a 'Binance Will Delist <tickers> on <date>'
announcement (spot delisting) from the first whole hour after release + 1 h, for 14 days, covered for good at +30% from the entry
close (one delisting position per coin; a coin can carry a listing and a delisting short, as in Gen468), total gross capped at 0.5, 10 bp per side, real funding.

Data: announcements research_data/binance_announcements/catalog_161.json + <live>/announcements/catalog_161.json; closes of a
delisting coin from the research pack (via binance_pack, which has its own live overlay), research_data/binance_extra (+ <live>/),
research_data/binance_pit, and <live>/events/<SYM>_1h.parquet / _funding.parquet (qpl.live.binance_public.update_event_coins)."""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

import listing_live as LL

ROOT = LL.ROOT
LIVE = LL.LIVE.parent if LL.LIVE is not None else None
CUT = LL.CUT
EX, PIT, ANN = ROOT / "research_data/binance_extra", LL.PIT, ROOT / "research_data/binance_announcements"
SIZE, CAP, HOLD, STOP, COST_BP, PIVOT, LO, HI = 0.05, 0.5, 14, 0.30, 10.0, 1.5, 0.5, 2.0
CROWD = json.loads((ROOT / "config/listing_crowding.json").read_text())["L"]


def crowding(sym: str, t0: pd.Timestamp) -> float:
    """Size multiplier of a listing (first bar t0): research value, else the live ratios known before the entry."""
    if sym in CROWD:
        L = CROWD[sym]
    else:
        f = LIVE / "listings" / f"{sym}_ratios.parquet" if LIVE is not None else None
        if f is None or not f.exists():
            return 1.0
        e = (t0 + pd.Timedelta(hours=24)).ceil("D"); x = pd.read_parquet(f)
        v = x.loc[(x.index >= e - pd.Timedelta(hours=24)) & (x.index < e), "count_long_short_ratio"].astype(float).dropna()
        if CUT is not None:
            v = v[v.index + pd.Timedelta(minutes=5) <= CUT]
        if len(v) <= 50:
            return 1.0
        L = float(v.mean())
    return float(np.clip(L / PIVOT, LO, HI))


def _tickers(s: str) -> list[str]:
    s = re.sub(r"\(.*?\)", " ", s)
    return [t for t in re.split(r"[,&\s]+|\band\b", s) if re.fullmatch(r"[A-Z0-9]{2,15}", t or "")]


def delistings(live: Path | None = LIVE, cut: pd.Timestamp | None = CUT) -> list[tuple[str, pd.Timestamp]]:
    """[(coin, release time)] of spot-delisting announcements known at the cutoff (Gen467 parsing); the paper's data update passes
    its live folder explicitly (the environment is set only for the hourly computation)."""
    arts = {}
    for f in (ANN / "catalog_161.json", (Path(live) / "announcements/catalog_161.json") if live is not None else None):
        if f is not None and f.exists():
            arts.update({a["id"]: a for a in json.loads(f.read_text())["articles"]})
    out = []
    for a in arts.values():
        t = pd.to_datetime(a["releaseDate"], unit="ms")
        if t < LL.FIRST or (cut is not None and t > cut):
            continue
        m = re.match(r"Binance Will Delist (.+?) on \d{4}-\d{2}-\d{2}", a["title"])
        if m and "Futures" not in a["title"]:
            out += [(x, t) for x in _tickers(m.group(1))]
    return sorted(out, key=lambda e: e[1])


def _closes(coin: str):
    """(hourly close, funding stamped at settlement) of coin's USDT perp, research + live overlays, cut; (None, None) if unknown."""
    from qpl.lab import binance_pack as B
    if coin in B.coins():
        cl = B.k5(coin).close.resample("1h").last().dropna(); fu = B.funding(coin).copy()
        cl.index = pd.DatetimeIndex(cl.index).as_unit("ns"); fu.index = pd.DatetimeIndex(fu.index).as_unit("ns").floor("h")
        return cl, fu.groupby(level=0).sum()
    sym, ks, fs = f"{coin}USDT", [], []
    for base in (EX, PIT, LIVE, LIVE / "events" if LIVE is not None else None):
        if base is None:
            continue
        if (base / f"{sym}_1h.parquet").exists():
            k = pd.read_parquet(base / f"{sym}_1h.parquet", columns=["close"])["close"].astype(float); k.index = pd.DatetimeIndex(k.index).as_unit("ns"); ks.append(k)
        if (base / f"{sym}_funding.parquet").exists():
            x = pd.read_parquet(base / f"{sym}_funding.parquet")
            fs.append(pd.Series(x["last_funding_rate"].astype(float).to_numpy(), index=pd.DatetimeIndex(pd.to_datetime(x["time"])).as_unit("ns").floor("h")))
    if not ks:
        return None, None
    cl = pd.concat(ks); cl = cl[~cl.index.duplicated(keep="last")].sort_index()
    fu = pd.concat(fs).groupby(level=0).last().sort_index() if fs else pd.Series(dtype=float)
    if CUT is not None:
        cl = cl[cl.index + pd.Timedelta(hours=1) <= CUT]; fu = fu[fu.index <= CUT]
    return cl, fu


def pnl(index: pd.DatetimeIndex):
    """(hourly P&L on `index`, positions frame, listing events) of the event-short sleeve."""
    tf = set(json.loads((ROOT / "config/tradfi_perps.json").read_text())["symbols"])
    EV = LL.events(); cap, LL.CAP = LL.CAP, 1e9
    try:
        PL = LL.positions(index, EV)
    finally:
        LL.CAP = cap
    CF = {s[:-4]: (c, f) for s, t0, c, f in EV}
    for s, t0, c, f in EV:
        if s[:-4] in PL:
            PL[s[:-4]] = PL[s[:-4]] * crowding(s, t0)
    PD = {}
    for coin, t in delistings():
        if coin in tf:
            continue
        cl, fu = _closes(coin)
        if cl is None or not ((cl.index >= t.floor("h") - pd.Timedelta(hours=2)) & (cl.index <= t.ceil("h"))).any():
            continue                                                  # the perp was not trading at the announcement
        start = t.ceil("h") + pd.Timedelta(hours=1); end = start + pd.Timedelta(days=HOLD); cc = cl.loc[start:end]
        if len(cc) == 0:
            continue
        hit = cc[cc >= cc.iloc[0] * (1 + STOP)].index; last = hit[0] if len(hit) else min(end, cl.index.max())
        p = pd.Series(-SIZE, index=cl.loc[start:last].index); p.index = p.index + pd.Timedelta(hours=1); p = p.reindex(index).fillna(0.0)
        p = p.where(cl.reindex(index - pd.Timedelta(hours=1)).notna().to_numpy(), 0.0)
        cur = PD.get(coin, pd.Series(0.0, index=index)); PD[coin] = cur.where(cur != 0, p); CF["spo_" + coin] = (cl, fu)
    P = pd.concat([PL, pd.DataFrame(PD, index=index).add_prefix("spo_")], axis=1).reindex(index).fillna(0.0)
    g = P.abs().sum(axis=1); P = P.mul((CAP / g).clip(upper=1.0).fillna(1.0), axis=0)
    out = pd.Series(0.0, index=index)
    for n in P.columns:
        c, f = CF[n]; p = P[n]; r = (c / c.shift(1) - 1).reindex(index).fillna(0.0)
        fu = f.copy(); fu.index = fu.index - pd.Timedelta(hours=1); fu = fu.groupby(level=0).sum().reindex(index).fillna(0.0)
        out = out + p * r - p * fu - p.diff().abs().fillna(p.abs()) * COST_BP / 1e4
    pos = P.T.groupby(lambda n: n[4:] if n.startswith("spo_") else n).sum().T            # by coin (a listing and a delisting can overlap)
    return out, pos, EV
