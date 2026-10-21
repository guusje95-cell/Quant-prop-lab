"""Paper trading of crypto portfolio v5 (config/paper_v5.json), v6, v7 (v6 + ridge ML, Gen109), bf, or the shadow books v6b/bfb (config/paper_<VER>.json; set QPL_PAPER).
Simulation only: public market data, no keys, no orders. v5 and v6 run side by side, each in its own folder.

  python scripts/paper_v5.py run          # once: update data, freeze the newly completed hours, write book + status
  python scripts/paper_v5.py loop         # keep running: every hour at :06 UTC (leave the window open, PC awake)
  python scripts/paper_v5.py status       # print the status (no download)
  python scripts/paper_v5.py reconcile    # recompute the paper period with the final data and compare with the frozen ledger
  python scripts/paper_v5.py selftest     # no-look-ahead proof on the research pack (cut the data at several moments)

Outputs in paper_trading/v5/: ledger_hourly.csv (frozen), daily.csv, book_next_hour.json, events.jsonl, status.md, reconcile.csv.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
VER = os.environ.get("QPL_PAPER", "v5")                   # "v5", "v6" (v5 + deleveraging bounce, Gen90), "bf" (CFD book), and the
BREADTH = VER in ("v6b", "bfb")                            # shadow books "v6b"/"bfb": premium carry on more coins (Gen80 / Gen121)
if VER == "bfb":
    os.environ["QPL_BREADTH"] = "1"                        # read by cfd_book (also in the child processes)
CFG = json.loads((ROOT / f"config/paper_{VER}.json").read_text())
OUT = ROOT / "paper_trading" / VER
DATA = OUT / "data"
PACK = ROOT / "research_data" / "binance"
SLEEVES = ["C*", "premium carry", "cascade limit strict", "trend 4h", "Weiss expiry"] + (["delev bounce"] if VER in ("v6", "v6b", "v7", "v8") else []) \
    + (["ridge ML"] if VER in ("v7", "v8") else []) + (["alt kimchi"] if VER == "v8" else [])
ALTK = "alt kimchi" in SLEEVES                            # v8: Gen247 A kimchi premium on altcoins (scripts/alt_kimchi.py, Upbit altcoin feeds)
RIDGE = "ridge ML" in SLEEVES                             # v7: Gen108 ridge on BTC/ETH (scripts/ridge_live.py, extra live inputs)
CFDBOOK = VER in ("bf", "bfb", "bf2")
if CFDBOOK:                                            # CFD book for BrightFunded 2-Step Classic swap-free (scripts/cfd_book.py)
    SLEEVES = ["C*", "premium carry", "trend 4h", "Weiss expiry", "delev bounce", "coinbase premium"]
    if VER == "bf2":                                   # Gen234: + ridge ML (CFD costs) + index CFD sleeve P6 + R1 + P1 (scripts/index_sleeve.py)
        SLEEVES += ["ridge ML", "vol-managed indices"]
    RIDGE = "ridge ML" in SLEEVES
INDEX = "vol-managed indices" in SLEEVES
SCALE = CFG["frozen"][f"{VER}_scale"]
BACKTEST = ROOT / {"v6": "results/cache_v6_final.parquet", "v7": "results/cache_v7_final.parquet", "v8": "results/cache_v8_final.parquet", "bf2": "results/cache_bf2_final.parquet", "bf": "results/cache_bf_final.parquet", "v6b": "results/cache_v6b_final.parquet",
                   "bfb": "results/cache_bfb_final.parquet"}.get(VER, "results/cache_gen72_final.parquet")


def extra_coins() -> list[str]:
    """Extra Binance coins the shadow book reads (none for v5/v6/bf)."""
    if not BREADTH:
        return []
    from qpl.lab import extra_pack as X
    return X.coins() if VER == "v6b" else [c for c in X.BF_NEW if c in X.coins()]
STOP_FRACTION = CFG["frozen"].get("stop_fraction", 0.5)


def utcnow() -> pd.Timestamp:
    return pd.Timestamp.now("UTC").tz_localize(None)


def locked(path: Path):
    print(f"  ({path.name} is open in another program, e.g. Excel - close it; it will be updated next hour)")


def log_event(kind: str, **kw):
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "events.jsonl", "a") as f:
        f.write(json.dumps({"wall_utc": str(utcnow()), "event": kind, **kw}, default=str) + "\n")


# ---------------------------------------------------------------- data coverage (which hours are complete everywhere)
def _end_of(path: Path, kind: str):
    if not path.exists():
        return None
    if kind == "5m":
        return pd.DatetimeIndex(pd.read_parquet(path, columns=["close"]).index).max() + pd.Timedelta(minutes=5)
    if kind == "1h":
        return pd.DatetimeIndex(pd.read_parquet(path, columns=["close"]).index).max() + pd.Timedelta(hours=1)
    if kind == "premium":
        return pd.to_datetime(pd.read_parquet(path, columns=["time"])["time"]).max() + pd.Timedelta(hours=1)
    if kind == "oi":
        return pd.to_datetime(pd.read_parquet(path, columns=["time"])["time"]).max() + pd.Timedelta(minutes=5)
    if kind == "spot":
        return pd.DatetimeIndex(pd.read_parquet(path).index).max() + pd.Timedelta(days=1)


def data_cutoff(live: bool) -> pd.Timestamp:
    """Latest whole hour at which every input the sleeves read is complete."""
    from qpl.lab import binance_pack as B0
    ends = []
    for coin in sorted(p.stem.replace("USDT_5m", "") for p in PACK.glob("*USDT_5m.parquet")):
        for name, kind in ((f"{coin}USDT_5m.parquet", "5m"), (f"{coin}USDT_premium_1h.parquet", "premium"),
                           (f"{coin}USDT_metrics.parquet", "oi")):
            e = [x for x in (_end_of(PACK / name, kind), _end_of(DATA / name, kind) if live else None) if x is not None]
            ends.append(max(e))
    for coin in extra_coins():                             # shadow books: extra coins' hourly klines and premium
        for name, kind in ((f"{coin}USDT_1h.parquet", "1h"), (f"{coin}USDT_premium_1h.parquet", "premium")):
            e = [x for x in (_end_of(ROOT / "research_data/binance_extra" / name, kind), _end_of(DATA / "extra" / name, kind) if live else None)
                 if x is not None]
            ends.append(max(e))
    cut = min(ends).floor("h")
    if CFDBOOK or RIDGE:                               # Coinbase candles count once their hour is over
        for prod in ("BTC-USD", "ETH-USD"):
            e = [pd.read_parquet(p).index.max() + pd.Timedelta(hours=1) for p in
                 (ROOT / f"research_data/coinbase/{prod}_1h.parquet", DATA / "coinbase" / f"{prod}_1h.parquet") if p.exists() and (live or "research" in str(p))]
            cut = min(cut, max(e).floor("h"))
    if INDEX:                                          # index CFD bars: wait at most one hour for a late Dukascopy bar (closed market: go on)
        last = max(max(pd.read_parquet(p).index.max() for p in (ROOT / f"research_data/dukascopy/{s}_1h.parquet", DATA / "dukascopy" / f"{s}_1h.parquet")
                       if p.exists() and (live or "research" in str(p))) for s in ("US100", "US500", "US30"))
        cut = min(cut, max(last + pd.Timedelta(hours=1), cut - pd.Timedelta(hours=1)))
    spot = [x for x in (_end_of(ROOT / "data/processed/crypto/binance_spot_majors_1d.parquet", "spot"),
                        _end_of(DATA / "binance_spot_majors_1d.parquet", "spot") if live else None) if x is not None]
    day_ok = max(spot)                                     # daily bars complete up to here
    if cut.floor("D") > day_ok:                            # cannot cross a midnight before yesterday's spot bar exists
        cut = day_ok
    return cut


def set_env(cutoff: pd.Timestamp, live: bool):
    os.environ["QPL_CUTOFF"] = str(cutoff)
    os.environ["QPL_END"] = str(cutoff - pd.Timedelta(hours=1))
    if live:
        os.environ["QPL_LIVE_PACK"] = str(DATA)
    else:
        os.environ.pop("QPL_LIVE_PACK", None)


# ---------------------------------------------------------------- compute (call after set_env, in a fresh process)
def compute():
    if CFDBOOK:
        return compute_bf()
    import crypto_sleeves as CS
    from qpl.lab import binance_pack as B
    END = pd.Timestamp(CS.END)
    cw = CS.cstar_weights(); pw = CS.premium_breadth_weights() if BREADTH else CS.premium_weights()
    cas, cpos = CS.cascade(limit=0.005, through=0.001, positions=True, live=True)
    tr, tpos = CS.trend4h(positions=True)
    we, wpos = CS.weiss_expiry(positions=True)
    cols = {"C*": CS._from_daily_weights(cw, B.MAJ10, 7.5),
            "premium carry": CS.premium_carry_breadth(w=pw) if BREADTH else CS._from_daily_weights(pw, B.coins(), 5),
            "cascade limit strict": cas, "trend 4h": tr, "Weiss expiry": we}
    if "delev bounce" in SLEEVES:
        bw = CS.delev_bounce_weights(); cols["delev bounce"] = CS._from_daily_weights(bw, list(bw.columns), 5)
    if RIDGE:
        import ridge_live as RL
        rw = RL.ridge_weights(); cols["ridge ML"] = CS._from_daily_weights(rw, list(rw.columns), 5)
    if ALTK:
        import alt_kimchi as AK
        aw = AK.weights(); cols["alt kimchi"] = CS._from_daily_weights(aw, list(aw.columns), 5)
    H = pd.DataFrame(cols)[SLEEVES].fillna(0.0).loc[:END]
    h1 = END + pd.Timedelta(hours=1)
    Hx = pd.concat([H, pd.DataFrame(0.0, index=[h1], columns=H.columns)])          # makes the next day's weights computable
    ph, W, mult = CS.portfolio_v5(Hx)
    ph = ph.loc[:END] * SCALE
    # ---- target book for the next hour (fractions of equity at risk 1.0)
    d = h1.floor("D")
    eff = (W.loc[d] * mult.get(d, np.nan) * SCALE) if d in W.index else pd.Series(np.nan, index=SLEEVES)
    expo = {}
    prev = cw.loc[:d - pd.Timedelta(days=1)]
    expo["C*"] = prev.iloc[-1] if len(prev) else pd.Series(dtype=float)
    prev = pw.loc[:d - pd.Timedelta(days=1)]
    expo["premium carry"] = prev.iloc[-1] if len(prev) else pd.Series(dtype=float)
    expo["trend 4h"] = tpos.loc[h1] if h1 in tpos.index else pd.Series(dtype=float)
    if "delev bounce" in SLEEVES:
        prev = bw.loc[:d - pd.Timedelta(days=1)]
        expo["delev bounce"] = prev.iloc[-1] if len(prev) else pd.Series(dtype=float)
    if RIDGE:
        prev = rw.loc[:d - pd.Timedelta(days=1)]
        expo["ridge ML"] = prev.iloc[-1] if len(prev) else pd.Series(dtype=float)
    if ALTK:
        prev = aw.loc[:d - pd.Timedelta(days=1)]
        expo["alt kimchi"] = prev.iloc[-1] if len(prev) else pd.Series(dtype=float)
    ot = cpos.attrs.get("open_trades", [])
    expo["cascade limit strict"] = pd.Series({t["coin"]: t["size"] for t in ot if pd.Timestamp(t["planned_exit"]) >= h1}, dtype=float)
    expo["Weiss expiry"] = pd.Series(dtype=float)
    last_fri = h1.dayofweek == 4 and (h1 + pd.Timedelta(days=7)).month != h1.month
    weiss_note = None
    if last_fri and h1.hour in (8, 9):
        side = {}
        for coin in ("BTC", "ETH"):
            k = B.k5(coin); t7 = h1.normalize() + pd.Timedelta(hours=7)
            p8 = k.close.loc[:h1.normalize() + pd.Timedelta(hours=7, minutes=55)].iloc[-1] if h1.hour == 8 else k.open.get(h1.normalize() + pd.Timedelta(hours=8))
            if t7 in k.index and p8 is not None:
                side[coin] = -np.sign(p8 / k.open[t7] - 1) / 2
        expo["Weiss expiry"] = pd.Series(side, dtype=float)
        weiss_note = "expiry trade: hold from 08:00 to 10:00 UTC"
    book = pd.Series(dtype=float); by = {}
    for s in SLEEVES:
        if len(expo[s]) and np.isfinite(eff.get(s, np.nan)):
            part = expo[s].astype(float) * float(eff[s]); by[s] = part
            book = book.add(part, fill_value=0.0)
    effd = W.mul(mult.reindex(W.index), axis=0) * SCALE                              # per-day sleeve multipliers
    return {"END": END, "H": H, "ph": ph, "eff": eff, "effd": effd, "book": book[book.abs() > 1e-6].sort_values(),
            "by_sleeve": pd.DataFrame(by).fillna(0.0),
            "pending": cpos.attrs.get("pending_signals", []), "open_cascade": ot, "weiss": weiss_note, "mult": mult}


def compute_bf():
    """CFD book (BrightFunded): same outputs as compute(). Gross exposure is capped at the 1:5 crypto leverage at the paper risk."""
    import crypto_sleeves as CS
    import cfd_book as CB
    from qpl.lab import binance_pack as B
    END = pd.Timestamp(CS.END); h1 = END + pd.Timedelta(hours=1)
    R, pos, daily = CB.positions()
    CSL = [s for s in SLEEVES if s != "vol-managed indices"]                          # crypto CFD sleeves
    if RIDGE:
        import ridge_live as RL
        pos["ridge ML"] = CB.d2h(RL.ridge_weights().reindex(columns=CB.CFD).fillna(0.0), pos["C*"].index)
    H = pd.DataFrame({s: CB.sleeve_pnl(pos[s], R) for s in CSL})
    if INDEX:
        import index_sleeve as IS
        ipos, ipnl = IS.sleeve(pos["C*"].index); pos["vol-managed indices"] = ipos; H["vol-managed indices"] = ipnl.reindex(R.index)
    H = H[SLEEVES].fillna(0.0).loc[:END]
    Hx = pd.concat([H, pd.DataFrame(0.0, index=[h1], columns=H.columns)])
    ph0, W, mult = CS.portfolio_v5(Hx)
    idx = ph0.index
    Wh = W.reindex(idx.floor("D")).set_axis(idx); mh = mult.reindex(idx.floor("D")).set_axis(idx)
    net = sum(pos[s].reindex(idx).fillna(0.0) * Wh[s].to_numpy()[:, None] for s in CSL).mul(mh * SCALE, axis=0)   # crypto 1:5 cap
    cap = CB.LEVERAGE_CAP / float(CFG["frozen"]["risk"])
    capf = (cap / net.abs().sum(axis=1)).clip(upper=1.0).fillna(1.0)
    ph = (ph0 * SCALE * capf).loc[:END]
    d = h1.floor("D")
    eff = (W.loc[d] * mult.get(d, np.nan) * SCALE) if d in W.index else pd.Series(np.nan, index=SLEEVES)
    expo = {s: pos[s].loc[h1] if h1 in pos[s].index else pd.Series(dtype=float) for s in SLEEVES}
    expo["Weiss expiry"] = pd.Series(dtype=float); weiss_note = None
    if h1.dayofweek == 4 and (h1 + pd.Timedelta(days=7)).month != h1.month and h1.hour in (8, 9):
        side = {}
        for coin in ("BTC", "ETH"):
            k = B.k5(coin); t7 = h1.normalize() + pd.Timedelta(hours=7)
            p8 = k.close.loc[:h1.normalize() + pd.Timedelta(hours=7, minutes=55)].iloc[-1] if h1.hour == 8 else k.open.get(h1.normalize() + pd.Timedelta(hours=8))
            if t7 in k.index and p8 is not None:
                side[coin] = -np.sign(p8 / k.open[t7] - 1) / 2
        expo["Weiss expiry"] = pd.Series(side, dtype=float); weiss_note = "expiry trade: hold from 08:00 to 10:00 UTC"
    book = pd.Series(dtype=float); by = {}
    for s in SLEEVES:
        if len(expo[s]) and np.isfinite(eff.get(s, np.nan)):
            part = expo[s].astype(float) * float(eff[s]); part = part[part.abs() > 1e-9]; by[s] = part
            book = book.add(part, fill_value=0.0)
    g = float(book[book.index.isin(CB.CFD)].abs().sum()) if len(book) else 0.0     # the 1:5 cap counts crypto CFDs (whole book scaled, as ph)
    if g > cap:
        book = book * cap / g; by = {k: v * cap / g for k, v in by.items()}
    effd = W.mul(mult.reindex(W.index), axis=0) * SCALE
    return {"END": END, "H": H, "ph": ph, "eff": eff, "effd": effd, "book": book[book.abs() > 1e-6].sort_values(),
            "by_sleeve": pd.DataFrame(by).fillna(0.0), "pending": [], "open_cascade": [], "weiss": weiss_note, "mult": mult}


# ---------------------------------------------------------------- account (rebuilt from the frozen ledger each time)
def account(L: pd.DataFrame, risk: float, firm_key: str):
    from qpl.lab import propfirms as PF
    f = PF.PRESETS[firm_key]; acct = float(CFG["frozen"]["account"])
    stop = STOP_FRACTION * f.daily_loss
    eq = acct; rows = []
    for day, g in L.groupby(L["hour"].dt.floor("D")):
        start = eq; low = eq; stopped = False
        for r in g["port"].to_numpy():
            if stopped:
                continue
            eq *= 1 + risk * r; low = min(low, eq)
            if eq / start - 1 <= -stop:
                eq *= 1 - 0.001; low = min(low, eq); stopped = True
        dl_floor = start - f.daily_loss * (acct if f.daily_basis == "initial" else start)
        rows.append({"day": day, "ret": eq / start - 1, "equity": eq, "intraday_low": low, "daily_stop_hit": stopped,
                     "firm_daily_breach": low < dl_floor, "firm_max_breach": low < acct * (1 - f.max_loss),
                     "target_reached": eq >= acct * (1 + f.targets[0])})
    return pd.DataFrame(rows)


def status_text(L: pd.DataFrame, Dd: pd.DataFrame, risk: float) -> str:
    bt = pd.read_parquet(BACKTEST)["portfolio"]
    btd = bt.groupby(bt.index.floor("D")).sum().loc["2023-01-01":] * risk
    lines = [f"# Paper trading {VER} - status ({utcnow():%Y-%m-%d %H:%M} UTC)", "",
             f"Simulation only. Account ${CFG['frozen']['account']:,.0f}, risk {risk}, firm rules: {CFG['frozen']['firm']}.", ""]
    if L.empty or Dd.empty:
        return "\n".join(lines + ["No completed paper hours yet."])
    n = len(Dd); r = Dd["ret"]; eq = Dd["equity"]
    dd = (eq / eq.cummax().clip(lower=CFG["frozen"]["account"]) - 1).min()
    z = (r.mean() - btd.mean()) / (btd.std() / np.sqrt(n))
    late = float(L["late"].mean())
    weiss_n = int((L.groupby(L["hour"].dt.floor("D"))["Weiss expiry"].apply(lambda x: (x != 0).any())).sum())
    verdict = ("too early" if n < 56 or weiss_n < 2 else ("STOP" if z < -2 or dd < -0.12 else ("EXTEND" if z <= -1 else "GO")))
    lines += [f"- Paper period: {L['hour'].min():%Y-%m-%d %H:00} to {L['hour'].max():%Y-%m-%d %H:00} UTC ({len(L)} hours, {n} days)",
              f"- Equity: ${eq.iloc[-1]:,.0f} ({eq.iloc[-1] / CFG['frozen']['account'] - 1:+.2%}), max drawdown {dd:.2%}",
              f"- Daily mean {r.mean():+.3%} vs backtest {btd.mean():+.3%} (z = {z:+.2f}); positive days {(r > 0).mean():.0%}",
              f"- Daily stop hits: {int(Dd['daily_stop_hit'].sum())}; firm daily-limit breaches: {int(Dd['firm_daily_breach'].sum())}; "
              f"max-loss breaches: {int(Dd['firm_max_breach'].sum())}",
              f"- Weiss expiry events: {weiss_n}; late hours: {late:.1%}",
              f"- Gate (config/paper_{VER}.json): **{verdict}**", "",
              "Sleeve P&L so far (sum of hourly returns, unit size): " +
              ", ".join(f"{s} {L[s].sum():+.2%}" for s in SLEEVES)]
    return "\n".join(lines)


# ---------------------------------------------------------------- commands
def cmd_run(a):
    OUT.mkdir(parents=True, exist_ok=True); DATA.mkdir(parents=True, exist_ok=True)
    if not a.no_download:
        from qpl.lab import binance_pack as B0
        from qpl.live import binance_public as BP
        print("updating public market data ...", flush=True)
        try:
            n = BP.update(PACK, DATA, B0.coins(), B0.MAJ10, now=utcnow(), spot_base=ROOT / "data/processed/crypto/binance_spot_majors_1d.parquet")
            print("  new rows:", n, flush=True)
        except BP.Restricted as e:
            log_event("DATA_REFUSED", msg=str(e)); print(e); return 2
        BP.stablecoins()
        if extra_coins():
            BP.update_extra(ROOT / "research_data/binance_extra", DATA / "extra", extra_coins(), now=utcnow())
        if CFDBOOK or RIDGE:
            from qpl.live import coinbase_public as CB
            for prod in ("BTC-USD", "ETH-USD"):
                CB.update(prod, out=DATA / "coinbase", base=ROOT / f"research_data/coinbase/{prod}_1h.parquet")
        if RIDGE:                                          # Upbit, USD/KRW, Deribit DVOL (missing updates: the ridge uses what it has)
            from qpl.live import ml_feeds
            if not ml_feeds.update(DATA, alts=ALTK):
                log_event("DATA_PARTIAL", msg="ridge ML inputs not fully updated")
        if INDEX:                                          # Dukascopy US100/US500/US30 hourly BID bars (same-day from tick files)
            from qpl.live import index_feed
            if not index_feed.update(DATA, now=utcnow()):
                log_event("DATA_PARTIAL", msg="index CFD bars not fully updated")
    cut = min(data_cutoff(live=True), utcnow().floor("h"))
    # compute in a child process so the loaders see the cutoff from the start
    r = subprocess.run([sys.executable, __file__, "_freeze", "--cutoff", str(cut), "--risk", str(a.risk), "--firm", a.firm]
                       + (["--start", a.start] if a.start else []), cwd=ROOT)
    return r.returncode


def cmd_freeze(a):
    cut = pd.Timestamp(a.cutoff); set_env(cut, live=True)
    t0 = time.time(); R = compute(); END = R["END"]
    led = OUT / "ledger_hourly.csv"
    L = pd.read_csv(led, parse_dates=["hour", "computed_at"]) if led.exists() else pd.DataFrame()
    if L.empty:
        first = paper_start(a.start, END + pd.Timedelta(hours=1), cut)
    else:
        first = L["hour"].max() + pd.Timedelta(hours=1)
    new = R["ph"].loc[first:END]
    if len(new):
        now = utcnow()
        rows = pd.DataFrame({"hour": new.index, **{s: R["H"][s].reindex(new.index).to_numpy() for s in SLEEVES},
                             **{f"w {s}": R["effd"][s].reindex(new.index.floor("D")).to_numpy() for s in SLEEVES},
                             "port": new.to_numpy(), "computed_at": now})
        rows["lag_h"] = (rows["computed_at"] - (rows["hour"] + pd.Timedelta(hours=1))).dt.total_seconds() / 3600
        rows["late"] = rows["lag_h"] > 2
        L2 = pd.concat([L, rows], ignore_index=True)
        try:
            tmp = led.with_suffix(".tmp"); L2.to_csv(tmp, index=False); tmp.replace(led); L = L2
        except PermissionError:                                 # hours stay unfrozen and are added (flagged late if > 2h) next run
            locked(led); new = new.iloc[:0]
    Dd = account(L, a.risk, a.firm) if len(L) else pd.DataFrame()
    if len(Dd):
        try:
            Dd.to_csv(OUT / "daily.csv", index=False)
        except PermissionError:
            locked(OUT / "daily.csv")
    h1 = END + pd.Timedelta(hours=1)
    eq = float(Dd["equity"].iloc[-1]) if len(Dd) else float(CFG["frozen"]["account"])
    by = (R["by_sleeve"] * eq * a.risk).round(2)
    book = {"for_hour_utc": str(h1), "made_at_utc": str(utcnow()), "data_cutoff_utc": str(cut), "equity": round(eq, 2), "risk": a.risk,
            "target_notional_usd": {k: round(v * eq * a.risk, 2) for k, v in R["book"].items()},
            "by_sleeve_usd": {c: {s_: v for s_, v in row.items() if abs(v) >= 0.01} for c, row in by.iterrows()},
            "cascade_limit_orders": R["pending"], "cascade_open_trades": R["open_cascade"], "weiss": R["weiss"],
            "sleeve_multipliers": {k: (None if not np.isfinite(v) else round(float(v), 4)) for k, v in R["eff"].items()},
            "note": "simulation only - no order is sent anywhere"}
    prev_file = OUT / "book_next_hour.json"
    prev = json.loads(prev_file.read_text()) if prev_file.exists() else None
    orders = simulated_orders(prev, book)
    if orders is not None:                                      # None: orders.csv locked -> keep the old book, diff again next hour
        try:
            prev_file.write_text(json.dumps(book, indent=1, default=str))
        except PermissionError:
            locked(prev_file)
        print_orders(book, orders)
    try:
        (OUT / "status.md").write_text(status_text(L, Dd, a.risk))
    except PermissionError:
        locked(OUT / "status.md")
    write_excel(L, Dd)
    log_event("RUN", cutoff=cut, new_hours=len(new), seconds=round(time.time() - t0, 1))
    print(f"frozen {len(new)} new hour(s) up to {END:%Y-%m-%d %H:00} UTC; book for {h1:%H:00} written ({time.time() - t0:.0f}s)")
    print(status_text(L, Dd, a.risk))
    return 0


MIN_ORDER_USD = 50.0          # smaller changes are ignored (a bot would not trade dust)


def simulated_orders(prev: dict | None, book: dict) -> pd.DataFrame:
    """Orders a bot would send at the start of book['for_hour_utc'] to move from the previous target to the new one.
    Appended to orders.csv. Simulation only."""
    new = book["target_notional_usd"]; old = prev["target_notional_usd"] if prev else {}
    nb = book.get("by_sleeve_usd", {}); ob = prev.get("by_sleeve_usd", {}) if prev else {}
    rows = []
    for coin in sorted(set(new) | set(old)):
        d = new.get(coin, 0.0) - old.get(coin, 0.0)
        if abs(d) < MIN_ORDER_USD:
            continue
        sl = set(nb.get(coin, {})) | set(ob.get(coin, {}))
        why = {s_: nb.get(coin, {}).get(s_, 0.0) - ob.get(coin, {}).get(s_, 0.0) for s_ in sl}
        why = ", ".join(f"{s_} {v:+,.0f}" for s_, v in sorted(why.items(), key=lambda kv: -abs(kv[1])) if abs(v) >= 1)
        rows.append({"hour_utc": book["for_hour_utc"], "coin": coin, "side": "BUY" if d > 0 else "SELL", "usd": round(abs(d), 2),
                     "from_usd": round(old.get(coin, 0.0), 2), "to_usd": round(new.get(coin, 0.0), 2),
                     "type": "initial position" if prev is None else "rebalance", "because": why})
    df = pd.DataFrame(rows)
    if len(df):
        f = OUT / "orders.csv"
        try:
            df.to_csv(f, mode="a", header=not f.exists(), index=False)
        except PermissionError:
            locked(f); return None
    return df


def print_orders(book: dict, orders: pd.DataFrame):
    h = pd.Timestamp(book["for_hour_utc"])
    print(f"\n=== Simulated orders at {h:%Y-%m-%d %H:00} UTC (paper only, nothing is sent) ===")
    if orders.empty:
        print("  no changes: keep the current positions")
    for o in orders.itertuples():
        print(f"  {o.side:4} {o.coin:5} ${o.usd:>10,.0f}   {o.from_usd:>+10,.0f} -> {o.to_usd:>+10,.0f}   ({o.because})")
    for x in book.get("cascade_limit_orders") or []:
        print(f"  LIMIT BUY {x['coin']} at {x['limit_price']:.6g}, valid 1 hour, stop {x['stop']:.6g} (cascade)")
    if book.get("weiss"):
        print(f"  {book['weiss']}")
    tgt = book["target_notional_usd"]
    gross = sum(abs(v) for v in tgt.values())
    print(f"  positions after: {len([v for v in tgt.values() if v > 0])} long / {len([v for v in tgt.values() if v < 0])} short, "
          f"gross ${gross:,.0f} on ${book['equity']:,.0f} equity")
    print(f"  full list: paper_trading/{VER}/orders.csv and book_next_hour.json\n")


def write_excel(L: pd.DataFrame, Dd: pd.DataFrame):
    """paper_trading/v5/paper_v5.xlsx: the same results with proper %, $ and date formats (CSV numbers use a decimal point,
    which Dutch Excel misreads). Skipped with a note if openpyxl is missing or the file is open in Excel."""
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        print("  (install openpyxl for the Excel file: pip install openpyxl)"); return
    path = OUT / f"paper_{VER}.xlsx"
    try:
        with pd.ExcelWriter(path, engine="openpyxl") as xw:
            if len(Dd):
                d = Dd.copy(); d["day"] = pd.to_datetime(d["day"]).dt.date
                d = d.rename(columns={"day": "Day (UTC)", "ret": "Return", "equity": "Equity $", "intraday_low": "Intraday low $",
                                      "daily_stop_hit": "Own daily stop hit", "firm_daily_breach": "Firm daily-loss breach",
                                      "firm_max_breach": "Firm max-loss breach", "target_reached": "10% target reached"})
                d.to_excel(xw, sheet_name="Daily", index=False)
            o = OUT / "orders.csv"
            if o.exists():
                od = pd.read_csv(o).rename(columns={"hour_utc": "Hour (UTC)", "coin": "Coin", "side": "Side", "usd": "Amount $",
                                                    "from_usd": "Position before $", "to_usd": "Position after $", "type": "Type",
                                                    "because": "Caused by (strategy $ change)"})
                od.iloc[::-1].to_excel(xw, sheet_name="Orders (newest first)", index=False)
            if len(L):
                h = L[["hour", "port"] + SLEEVES + ["late"]].copy()
                h = h.rename(columns={"hour": "Hour (UTC)", "port": "Portfolio return (risk 1.0)", "late": "Computed late"})
                h.iloc[::-1].to_excel(xw, sheet_name="Hourly (newest first)", index=False)
            st = (OUT / "status.md").read_text().splitlines() if (OUT / "status.md").exists() else []
            pd.DataFrame({"Status": [x.lstrip("#- ").replace("**", "") for x in st if x.strip()]}).to_excel(xw, sheet_name="Status", index=False)
            fmt = {"Return": "0.00%", "Equity $": "#,##0.00", "Intraday low $": "#,##0.00", "Amount $": "#,##0", "Position before $": "#,##0",
                   "Position after $": "#,##0", "Portfolio return (risk 1.0)": "0.000%", **{s_: "0.000%" for s_ in SLEEVES}}
            for ws in xw.book.worksheets:
                for col in ws.iter_cols(min_row=1, max_row=1):
                    name = col[0].value; letter = col[0].column_letter
                    ws.column_dimensions[letter].width = max(12, min(45, len(str(name)) + 4))
                    if name in fmt:
                        for c in ws[letter][1:]:
                            c.number_format = fmt[name]
                ws.freeze_panes = "A2"
    except PermissionError:
        print(f"  (paper_{VER}.xlsx is open in Excel; close it to let it refresh next hour)")


def paper_start(requested: str | None, default: pd.Timestamp, cut: pd.Timestamp) -> pd.Timestamp:
    """The first paper hour, fixed once (state.json). Older installs: the earliest START event in events.jsonl."""
    st = OUT / "state.json"
    if st.exists():
        return pd.Timestamp(json.loads(st.read_text())["first_hour"])
    first = None
    ev = OUT / "events.jsonl"
    if ev.exists():
        starts = [json.loads(x) for x in ev.read_text().splitlines() if '"START"' in x]
        if starts:
            first = min(pd.Timestamp(e["first_hour"]) for e in starts)
    if first is None:
        first = pd.Timestamp(requested) if requested else default
        log_event("START", first_hour=first, cutoff=cut)
    st.write_text(json.dumps({"first_hour": str(first)}))
    return first


def cmd_loop(a):
    from qpl.live.keepawake import keep_awake
    keep_awake()
    while True:
        try:
            cmd_run(a)
        except Exception as e:                                 # keep going; the next run catches up the missed hours
            log_event("ERROR", msg=repr(e)); print("error:", e)
        nxt = utcnow().floor("h") + pd.Timedelta(hours=1, minutes=6)
        print(f"next run at {nxt:%H:%M} UTC", flush=True)
        time.sleep(max(30, (nxt - utcnow()).total_seconds()))


def cmd_status(a):
    L = pd.read_csv(OUT / "ledger_hourly.csv", parse_dates=["hour", "computed_at"]) if (OUT / "ledger_hourly.csv").exists() else pd.DataFrame()
    Dd = account(L, a.risk, a.firm) if len(L) else pd.DataFrame()
    print(status_text(L, Dd, a.risk))


def cmd_reconcile(a):
    L = pd.read_csv(OUT / "ledger_hourly.csv", parse_dates=["hour", "computed_at"])
    cut = L["hour"].max() + pd.Timedelta(hours=1)
    r = subprocess.run([sys.executable, __file__, "_dump", "--cutoff", str(cut), "--live", "1", "--out", str(OUT / "_recompute.parquet")], cwd=ROOT)
    if r.returncode:
        return r.returncode
    X = pd.read_parquet(OUT / "_recompute.parquet").reindex(L["hour"])
    rep = pd.DataFrame({"hour": L["hour"], "frozen": L["port"].to_numpy(), "recomputed": X["port"].to_numpy()})
    for s in SLEEVES:
        rep[f"{s} diff"] = L[s].to_numpy() - X[s].to_numpy()
    rep["diff"] = rep["frozen"] - rep["recomputed"]; rep.to_csv(OUT / "reconcile.csv", index=False)
    corr = rep[["frozen", "recomputed"]].corr().iloc[0, 1]; cum = (rep["frozen"] - rep["recomputed"]).sum() * a.risk
    ok = (corr >= 0.99 or rep["diff"].abs().max() < 1e-9) and abs(cum) <= 0.005
    msg = f"reconcile: {len(rep)} hours, correlation {corr:.4f}, cumulative difference {cum:+.3%} of the account -> {'OK' if ok else 'INVESTIGATE'}"
    worst = rep.reindex(rep["diff"].abs().sort_values(ascending=False).index).head(5)
    print(msg); print(worst[["hour", "frozen", "recomputed"] + [f"{s} diff" for s in SLEEVES]].to_string(index=False))
    log_event("RECONCILE", ok=ok, corr=corr, cum=cum)
    return 0


def cmd_dump(a):
    """Child process: compute with data cut at --cutoff and save hourly sleeves + portfolio (+ book) to --out."""
    set_env(pd.Timestamp(a.cutoff), live=bool(int(a.live)))
    R = compute()
    X = R["H"].copy(); X["port"] = R["ph"].reindex(X.index)
    X.to_parquet(a.out)
    Path(a.out).with_suffix(".book.json").write_text(json.dumps({k: float(v) for k, v in R["book"].items()}))
    return 0


def cmd_selftest(a):
    """No-look-ahead proof: P&L of every hour computed with only the data up to that hour must equal the P&L computed with all
    later data. Uses the research pack (no download)."""
    tmp = OUT / "_selftest"; tmp.mkdir(parents=True, exist_ok=True)
    cuts = ["2026-09-01 01:00", "2026-09-14 00:00", "2026-09-21 13:00", "2026-09-25 09:00", "2026-09-25 10:00", "2026-09-25 11:00",
            "2026-09-28 05:00",
            "2026-09-30 17:00"]
    if ALTK:                                          # around 00:00 UTC, when the altcoin kimchi weights change
        cuts += ["2026-09-29 23:00", "2026-09-30 00:00", "2026-09-30 01:00"]
    if "delev bounce" in SLEEVES:                     # moments inside deleveraging-bounce holds (signal days 2026-04-12/13, 2026-05-15)
        cuts += ["2026-04-14 02:00", "2026-05-16 00:00", "2026-05-16 13:00", "2026-05-17 21:00"]
    if INDEX:                                         # around the index signals: R1 entry 14:00 ET and P1 entry 16:00 ET (EDT = UTC-4)
        cuts += ["2026-09-23 17:00", "2026-09-23 18:00", "2026-09-23 19:00", "2026-09-23 20:00", "2026-09-23 21:00", "2026-09-29 20:00"]
    full = tmp / "full.parquet"
    subprocess.run([sys.executable, __file__, "_dump", "--cutoff", "2026-10-01 00:00", "--live", "0", "--out", str(full)], cwd=ROOT, check=True)
    F = pd.read_parquet(full); worst = 0.0; ok = True
    for c in cuts:
        out = tmp / f"cut_{c.replace(' ', '_').replace(':', '')}.parquet"
        subprocess.run([sys.executable, __file__, "_dump", "--cutoff", c, "--live", "0", "--out", str(out)], cwd=ROOT, check=True)
        X = pd.read_parquet(out)
        last = X.index.max(); win = X.loc[last - pd.Timedelta(hours=71):last]
        d = (win - F.reindex(win.index)).abs()
        m = float(d.max().max()); worst = max(worst, m)
        bad = d.max()[d.max() > 1e-12]
        print(f"cutoff {c}: last hour {last}, max |difference| over the last 72 hours = {m:.2e}" + (f"  MISMATCH in {list(bad.index)}" if len(bad) else ""))
        ok &= len(bad) == 0
    print("SELFTEST", "PASSED: no look-ahead, frozen hours equal the final recomputation" if ok else "FAILED")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("run", "loop", "status", "reconcile", "_freeze"):
        p = sub.add_parser(name)
        p.add_argument("--risk", type=float, default=CFG["frozen"]["risk"]); p.add_argument("--firm", default=CFG["frozen"]["firm"])
        p.add_argument("--start", help="first paper hour (UTC), default: the next completed hour")
        p.add_argument("--no-download", action="store_true")
        if name == "_freeze":
            p.add_argument("--cutoff", required=True)
    p = sub.add_parser("_dump"); p.add_argument("--cutoff", required=True); p.add_argument("--live", default="1"); p.add_argument("--out", required=True)
    sub.add_parser("selftest")
    a = ap.parse_args()
    return {"run": cmd_run, "loop": cmd_loop, "status": cmd_status, "reconcile": cmd_reconcile, "_freeze": cmd_freeze,
            "_dump": cmd_dump, "selftest": cmd_selftest}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main() or 0)
