"""Hub-native paper engine: independent paper accounts for any Backtest Lab strategy (built-in or a plug-in in strategies_user/)
and for portfolios of several strategies, run forward bar by bar on live public market data. Simulation only: no exchange
account, no API keys, no orders anywhere.

Accounting is EXACTLY the Lab backtest's (qpl.lab.engine.run): the target weights decided at the close of bar t are held during
bar t+1; the cost of a rebalance (|change in weights| x cost_bps) is booked in the bar in which the new holding starts; funding is
charged on held weights at each funding stamp inside the bar (real Binance funding when the provider has it). A replay over
history therefore reproduces the backtest, which `tests/test_hub.py::test_paper_engine_matches_backtest` checks.

Safety / reliability: each bar is processed in one transaction and recorded once (primary keys), so a retry or restart can never
double-count; state (last bar, equity, held weights, pending cost) is in the database; a stale or missing latest bar stops the
account for that run (fail closed) and raises an alert; paused / stopped accounts are skipped; a reset is a NEW account (the old
one is kept); every configuration is stored with the account and never edited."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from qpl.hub.db import ROOT, alert, audit, db_path, now, tx
from qpl.lab import data as LD
from qpl.lab import engine as LE
from qpl.lab import strategies as LS

FREQ_TD = {"1h": pd.Timedelta(hours=1), "4h": pd.Timedelta(hours=4), "1d": pd.Timedelta(days=1)}


# ------------------------------------------------------------------------------------------------------------ data providers
class HistoricalProvider:
    """Replays given Bars (and optional funding series per symbol) as if they arrived live: bars(…, end) returns only bars that
    are complete at `end`."""

    def __init__(self, bars: LD.Bars, funding: dict | None = None):
        self.b = bars; self.f = funding or {}

    def bars(self, symbols, freq, start, end) -> LD.Bars:
        step = FREQ_TD[self.b.freq]
        b = self.b.select(symbols, start, pd.Timestamp(end) - step)            # bar labelled t is complete at t + step
        return LD.resample(b, freq) if freq != self.b.freq else b

    def funding(self, symbol, start, end) -> pd.Series:
        f = self.f.get(symbol)
        if f is None or f.empty:
            return pd.Series(dtype=float)
        return f.loc[(f.index > start) & (f.index <= end)]


class BinanceFuturesProvider:
    """Live public data: Binance USDT-M perpetual hourly klines + funding (fapi, no key), cached in hub_data/market. Run where
    Binance futures market data is reachable (the user's PC, like the paper trader)."""

    def __init__(self, cache: Path | None = None):
        self.cache = cache or db_path().parent / "market"; self.cache.mkdir(parents=True, exist_ok=True)

    def _hourly(self, sym: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
        from qpl.live import binance_public as BP
        f = self.cache / f"{sym}_1h.parquet"
        old = pd.read_parquet(f) if f.exists() else pd.DataFrame()
        frm = (old.index.max() + pd.Timedelta(hours=1)) if len(old) else start
        if frm < end:
            new = BP._klines(BP.Client(), f"{BP.FAPI}/fapi/v1/klines", sym, "1h", frm, end)
            if len(new):
                old = pd.concat([old, new[["open", "high", "low", "close", "volume"]].astype(float)]); old = old[~old.index.duplicated(keep="last")].sort_index()
                old.to_parquet(f)
        return old.loc[start:end - pd.Timedelta(hours=1)] if len(old) else old

    def bars(self, symbols, freq, start, end) -> LD.Bars:
        frames = {s: self._hourly(s, pd.Timestamp(start), pd.Timestamp(end)) for s in symbols}
        long = pd.concat([d.assign(symbol=s, time=d.index) for s, d in frames.items() if len(d)], ignore_index=True)
        b = LD.from_long(long, "Binance USDT-M perps (live)", "1h"); b.periods_per_year = LD.PPY["1h"]
        return LD.resample(b, freq) if freq != "1h" else b

    def funding(self, symbol, start, end) -> pd.Series:
        from qpl.live import binance_public as BP
        d = BP.Client().get(f"{BP.FAPI}/fapi/v1/fundingRate", {"symbol": symbol, "startTime": BP._ms(start), "endTime": BP._ms(end), "limit": 1000}) or []
        s = pd.Series([float(x["fundingRate"]) for x in d], index=pd.to_datetime([int(x["fundingTime"]) for x in d], unit="ms"))
        return s.loc[(s.index > start) & (s.index <= end)]


# ------------------------------------------------------------------------------------------------------------ accounts
def strategies() -> list[str]:
    return sorted(LS.registry()[0])


def _strategy(name: str):
    reg, _ = LS.registry()
    if name not in reg:
        raise KeyError(f"unknown Lab strategy '{name}'. Available: {sorted(reg)}")
    return reg[name]()


def create_account(c: sqlite3.Connection, key: str, config: dict, capital: float = 100_000.0, actor: str = "user") -> int:
    """config (strategy account): {"kind": "strategy", "strategy": <Lab name>, "params": {...}, "symbols": [...], "freq": "1h"|"4h"|"1d",
    "sizing": {Lab engine Config fields: cost_bps, asset_vol_target, max_asset_weight, leverage, ...}, "lookback_days": 400}
    config (portfolio account): {"kind": "portfolio", "members": [{<strategy config>, "weight": w}, ...], "freq": ..., "cost_bps": ..., "gross_cap": 3.0}"""
    full = f"engine:{key}"
    if c.execute("SELECT 1 FROM paper_accounts WHERE key=?", (full,)).fetchone():
        raise ValueError(f"{full} exists; accounts are immutable (create a new key to change anything)")
    members = config["members"] if config["kind"] == "portfolio" else [config]
    for m in members:
        _strategy(m["strategy"])
        if m.get("freq", config.get("freq", "1h")) not in FREQ_TD:
            raise ValueError("freq must be 1h, 4h or 1d")
    with tx(c):
        i = c.execute("INSERT INTO paper_accounts (key, source_dir, initial_capital, status, config, created_at) VALUES (?,?,?,?,?,?)",
                      (full, "hub paper engine", capital, "running", json.dumps(config), now())).lastrowid
        c.execute("INSERT INTO paper_engine_state (account_id, last_bar, equity, held, pending_cost, updated_at) VALUES (?,?,?,?,?,?)",
                  (i, None, capital, "{}", 0.0, now()))
        audit(c, actor, "create_paper_account", "paper_accounts", i, {"key": full, "config": config, "capital": capital})
    return i


def set_status(c: sqlite3.Connection, key: str, status: str, reason: str, actor: str = "user"):
    if status not in ("running", "paused", "stopped"):
        raise ValueError(status)
    with tx(c):
        n = c.execute("UPDATE paper_accounts SET status=? WHERE key=? AND key LIKE 'engine:%' AND status<>'archived'", (status, key)).rowcount
        audit(c, actor, f"paper_{status}", "paper_accounts", key, {"reason": reason, "changed": n})


def reset(c: sqlite3.Connection, key: str, new_key: str, reason: str, actor: str = "user") -> int:
    """'Reset' = archive the old account (all its records stay) and start a new one with the same configuration."""
    r = c.execute("SELECT config, initial_capital FROM paper_accounts WHERE key=?", (key,)).fetchone()
    with tx(c):
        c.execute("UPDATE paper_accounts SET status='archived' WHERE key=?", (key,)); audit(c, actor, "paper_reset", "paper_accounts", key, {"reason": reason, "new": new_key})
    return create_account(c, new_key, json.loads(r["config"]), r["initial_capital"], actor)


def _targets(cfg: dict, provider, end: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Target weights for every bar of the lookback window (Lab signal + Lab sizing) and the close prices; portfolios sum their
    members' weights x allocation (positions net out per coin)."""
    members = cfg["members"] if cfg["kind"] == "portfolio" else [dict(cfg, weight=1.0)]
    Ws, closes = [], []
    for m in members:
        freq = m.get("freq", cfg.get("freq", "1h")); look = pd.Timedelta(days=m.get("lookback_days", 400))
        b = provider.bars(m["symbols"], freq, end - look, end)
        if b.close.empty:
            raise RuntimeError("no market data returned")
        b.periods_per_year = LD.PPY[freq]
        s = _strategy(m["strategy"]); p = {**s.defaults(), **m.get("params", {})}
        sig = s.signal(b, p); scfg = LE.Config(**{k: v for k, v in m.get("sizing", {}).items() if k in LE.Config.__dataclass_fields__})
        W = LE.size(b, sig, scfg, getattr(s, "sizing", "engine")); Ws.append(W * float(m.get("weight", 1.0))); closes.append(b.close)
    idx = Ws[0].index
    for W in Ws[1:]:
        idx = idx.union(W.index)
    W = sum(w.reindex(idx).ffill().fillna(0.0) for w in Ws) if len(Ws) > 1 else Ws[0]
    W = W.T.groupby(level=0).sum().T
    cap = float(cfg.get("gross_cap", 0) or 0)
    if cap > 0:
        g = W.abs().sum(axis=1); W = W.mul((cap / g).clip(upper=1.0).fillna(1.0), axis=0)
    C = pd.concat(closes, axis=1); C = C.T.groupby(level=0).last().T.reindex(idx).ffill()
    return W, C


def step(c: sqlite3.Connection, key: str, provider, end: pd.Timestamp | None = None, replay_from: str | None = None) -> dict:
    """Process every bar of `key` completed since its last processed bar (forward paper). `replay_from` (tests / an explicit
    backfill) starts from that bar instead; replayed hours are marked retro=1."""
    a = c.execute("SELECT id, status, config, initial_capital, created_at FROM paper_accounts WHERE key=?", (key,)).fetchone()
    if a is None:
        raise KeyError(key)
    if a["status"] != "running":
        return {"status": a["status"], "processed": 0}
    cfg = json.loads(a["config"]); end = pd.Timestamp(end or now()).floor("h")
    freq = cfg.get("freq", "1h") if cfg["kind"] == "portfolio" else cfg.get("freq", "1h")
    st = c.execute("SELECT * FROM paper_engine_state WHERE account_id=?", (a["id"],)).fetchone()
    W, C = _targets(cfg, provider, end)
    last_complete = W.index.max(); expected = end.floor({"1h": "h", "4h": "4h", "1d": "D"}[freq]) - FREQ_TD[freq]
    if last_complete < expected:                                                            # fail closed on stale / missing data
        with tx(c):
            alert(c, "warning", f"paper:{key}", f"stale market data: last complete bar {last_complete}, expected {expected}", dedup_key=f"stale:{key}:{expected}")
        return {"status": "stale data", "last_complete": str(last_complete), "expected": str(expected), "processed": 0}
    held = {k: float(v) for k, v in json.loads(st["held"]).items()}; equity = float(st["equity"]); pending = float(st["pending_cost"])
    last = pd.Timestamp(st["last_bar"]) if st["last_bar"] else None
    if last is None:
        last = pd.Timestamp(replay_from) - FREQ_TD[freq] if replay_from else last_complete      # forward paper starts at the latest complete bar
        first_decision = True
    else:
        first_decision = False
    new = W.index[W.index > last] if not first_decision or replay_from else W.index[W.index >= last]
    defined = pd.Timestamp(a["created_at"]); n = 0; fees = 0.0
    R = C.pct_change(fill_method=None)
    for t in new:
        with tx(c):
            if not (first_decision and t == last and not replay_from):
                r = R.loc[t].fillna(0.0) if t in R.index else pd.Series(dtype=float)
                gross = sum(w * float(r.get(k, 0.0)) for k, w in held.items())
                fund = 0.0
                if hasattr(provider, "funding") and held:
                    for k, w in held.items():
                        if w:
                            fund += w * float(provider.funding(k, t, t + FREQ_TD[freq]).sum())
                ret = gross - fund - pending; equity *= (1 + ret)
                c.execute("INSERT OR IGNORE INTO paper_equity (account_id, ts, ret, equity, late, retro) VALUES (?,?,?,?,?,?)",
                          (a["id"], str(t), ret, equity, 0, int(t < defined)))
            tgt = W.loc[t].fillna(0.0); tgt = tgt[tgt.abs() > 1e-12]
            coins = set(tgt.index) | set(held)
            cost_bps = cfg.get("cost_bps", cfg.get("sizing", {}).get("cost_bps", LE.Config.cost_bps))
            trades = {k: float(tgt.get(k, 0.0)) - held.get(k, 0.0) for k in coins}
            pending = sum(abs(v) for v in trades.values()) * cost_bps / 1e4
            px = C.loc[t] if t in C.index else pd.Series(dtype=float)
            for k, d in trades.items():
                if abs(d) > 1e-12:
                    c.execute("INSERT OR IGNORE INTO paper_fills (account_id, ts, coin, delta_weight, price, notional_usd, cost_usd) VALUES (?,?,?,?,?,?,?)",
                              (a["id"], str(t), k, d, float(px.get(k, np.nan)), d * equity, abs(d) * equity * cost_bps / 1e4))
            for k, w in tgt.items():
                c.execute("INSERT OR IGNORE INTO paper_positions (account_id, ts, coin, weight, notional_usd) VALUES (?,?,?,?,?)",
                          (a["id"], str(t), k, float(w), float(w) * equity))
            held = {k: float(v) for k, v in tgt.items()}; fees += pending * equity
            c.execute("UPDATE paper_engine_state SET last_bar=?, equity=?, held=?, pending_cost=?, updated_at=? WHERE account_id=?",
                      (str(t), equity, json.dumps(held), pending, now(), a["id"]))
            c.execute("UPDATE paper_accounts SET last_ingested_at=?, last_data_ts=? WHERE id=?", (now(), str(t), a["id"]))
        n += 1; first_decision = False
    return {"status": "ok", "processed": n, "equity": equity, "last_bar": str(W.index.max())}


def step_all(c: sqlite3.Connection, provider=None) -> dict:
    provider = provider or BinanceFuturesProvider(); out = {}
    for r in c.execute("SELECT key FROM paper_accounts WHERE key LIKE 'engine:%' AND status='running'").fetchall():
        try:
            out[r["key"]] = step(c, r["key"], provider)
        except Exception as e:                                             # noqa: BLE001 - one account must not stop the others
            with tx(c):
                alert(c, "warning", f"paper:{r['key']}", f"paper engine error: {e}", dedup_key=f"engine_err:{r['key']}:{now()[:13]}")
            out[r["key"]] = {"status": "error", "error": str(e)}
    return out


def backtest_same_config(cfg: dict, provider, start: str, end: str) -> pd.Series:
    """The Lab backtest of the same configuration over [start, end] (net per bar), for backtest-vs-paper comparison."""
    W, C = _targets(cfg, provider, pd.Timestamp(end))
    wp = W.shift(1).fillna(0.0); ret = C.pct_change(fill_method=None).fillna(0.0)
    turn = wp.diff().abs().fillna(wp.abs())
    cost_bps = cfg.get("cost_bps", cfg.get("sizing", {}).get("cost_bps", LE.Config.cost_bps))
    return ((wp * ret).sum(axis=1) - turn.sum(axis=1) * cost_bps / 1e4).loc[start:end]
