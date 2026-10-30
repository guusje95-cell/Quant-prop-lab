"""Idempotent ingestion of everything the project already recorded. Nothing is modified at the source; re-running only adds what is new.

  legacy_registry()  research_database/experiments.sqlite (Gen1-25 variants) -> hypotheses + experiments (kind 'legacy_variant')
  protocols()        config/*protocol*.json + results/<gen>*.json (Gen26+) and research/v99/*_protocol.json + results/v99/*.json
  strategies()       the strategies and books of the project (v9.8 sleeves and book, futures book, CFD book) -> registry
  paper_accounts()   paper_trading/<ver>/ledger_hourly.csv, orders.csv, events.jsonl (shared from the user's PC) -> paper tables
  datasets()         research_data/* catalogue with freshness"""
from __future__ import annotations

import glob
import json
import re
import sqlite3
from pathlib import Path

import pandas as pd

from qpl.hub import experiments as EX
from qpl.hub import registry as RG
from qpl.hub.db import ROOT, audit, now, tx


def legacy_registry(c: sqlite3.Connection, path: Path = ROOT / "research_database/experiments.sqlite") -> dict:
    if not path.exists():
        return {"status": "missing", "path": str(path)}
    src = sqlite3.connect(path); src.row_factory = sqlite3.Row; n_h = n_e = 0
    for h in src.execute("SELECT * FROM hypotheses"):
        if not c.execute("SELECT 1 FROM hypotheses WHERE key=?", (f"legacy:{h['id']}",)).fetchone():
            EX.add_hypothesis(c, f"legacy:{h['id']}", (h["doc"] or h["id"])[:2000], family=h["family"], source="research_database/experiments.sqlite",
                              registered_at=None); n_h += 1
            with tx(c):
                c.execute("UPDATE hypotheses SET status=?, verdict=? WHERE key=?", (h["status"] or "closed", h["verdict"], f"legacy:{h['id']}"))
    have = {r[0] for r in c.execute("SELECT key FROM experiments WHERE source='research_database/experiments.sqlite'")}
    rows = [r for r in src.execute("SELECT * FROM experiments") if f"legacy:{r['id']}" not in have]
    with tx(c):
        for r in rows:
            hid = c.execute("SELECT id FROM hypotheses WHERE key=?", (f"legacy:{r['hypothesis_id']}",)).fetchone()
            c.execute("INSERT INTO experiments (key, hypothesis_id, kind, title, config, config_hash, code_version, data_version, periods, registered_at, "
                      "status, finished_at, metrics, decision, reason, trials_added, uses_holdout, source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (f"legacy:{r['id']}", hid["id"] if hid else None, "legacy_variant", f"{r['family']} / {r['strategy']} / {r['instrument']}",
                       r["params"], None, r["code_version"], r["data_version"],
                       json.dumps({"stage": r["stage"], "period": r["period"], "train": r["train_period"], "validation": r["validation_period"], "oos": r["oos_period"]}),
                       r["ts"], "done", r["ts"], r["metrics"], r["decision"], r["reason"], 1, int(str(r["stage"] or "").upper().startswith(("HOLD", "FINAL", "OOS"))),
                       "research_database/experiments.sqlite"))
            n_e += 1
        audit(c, "ingest", "legacy_registry", "experiments", None, {"hypotheses": n_h, "experiments": n_e})
    return {"hypotheses_added": n_h, "experiments_added": n_e}


_GEN = re.compile(r"(?:crypto_)?gen(\d+[a-z]?)_protocol\.json$")


def _result_files(tag: str) -> list[str]:
    base = ROOT / "results"
    return sorted({str(Path(p).relative_to(ROOT)) for p in glob.glob(str(base / f"{tag}.json")) + glob.glob(str(base / f"{tag}[a-z].json"))
                   + glob.glob(str(base / f"{tag}_*.json"))})


def _decision(res: dict | None) -> tuple[str, str]:
    if not isinstance(res, dict):
        return "no result file", ""
    for k in ("pass", "promote", "adopted"):
        if k in res and isinstance(res[k], bool):
            return ("pass" if res[k] else "fail"), f"result field '{k}'"
    return "see result / LEADERBOARD", ""


def protocols(c: sqlite3.Connection) -> dict:
    files = sorted(glob.glob(str(ROOT / "config/*protocol*.json"))) + sorted(glob.glob(str(ROOT / "research/v99/*_protocol.json")))
    added = bad = 0
    for f in files:
        rel = str(Path(f).relative_to(ROOT)); key = "protocol:" + rel
        if c.execute("SELECT 1 FROM experiments WHERE key=?", (key,)).fetchone():
            continue
        try:
            p = json.loads(Path(f).read_text())
        except Exception as e:                                   # noqa: BLE001 - keep a record that the file exists but cannot be parsed
            p = {"_unparseable": str(e)}; bad += 1
        m = _GEN.search(Path(f).name); tag = ("gen" + m.group(1)) if m else None
        if rel.startswith("research/v99/"):
            tag = None; rfiles = sorted(str(Path(x).relative_to(ROOT)) for x in glob.glob(str(ROOT / "results/v99" / (Path(f).stem.replace("_protocol", "") + "*.json"))))
        else:
            rfiles = _result_files(tag) if tag else []
        res = None
        if rfiles:
            try:
                res = json.loads((ROOT / rfiles[0]).read_text())
            except Exception:                                    # noqa: BLE001
                res = None
        dec, why = _decision(res)
        t = p.get("trials_added")
        trials = int(t) if isinstance(t, (int, float)) else (len(p["trials"]) if isinstance(p.get("trials"), dict) else 1)
        reg = str(p.get("registered") or p.get("date") or p.get("_written") or "")[:10] or None
        title = p.get("title") or p.get("hypothesis") or p.get("question") or p.get("idea") or (p.get("generation") or tag or rel)
        kind = "descriptive" if "descriptive" in json.dumps(p).lower()[:400] and not p.get("pass") else "protocol"
        EX.register(c, key, kind, p, title=str(title)[:300], trials_added=trials, source=rel, registered_at=reg,
                    status="done" if rfiles else "registered", periods=None)
        with tx(c):
            c.execute("UPDATE experiments SET metrics=?, decision=?, reason=?, artifacts=?, finished_at=? WHERE key=?",
                      (json.dumps(res, default=str)[:200_000] if res is not None else None, dec, why, json.dumps(rfiles),
                       reg if rfiles else None, key))
        added += 1
    with tx(c):
        audit(c, "ingest", "protocols", "experiments", None, {"added": added, "unparseable": bad})
    return {"protocols_added": added, "unparseable": bad}


SLEEVES_V98 = {
    "C*": ("crypto_sleeves.cstar_pit_weights + breadth_pnl(7.5 bp)", "momentum / trend", "point-in-time top-10 perps, CStarTrend signal, own-size sizing"),
    "trend 4h": ("basket_live.trend_ensemble", "trend", "BTC/ETH/SOL 4-hour Donchian ensemble 15/20/30"),
    "Weiss expiry": ("crypto_sleeves.weiss_expiry", "event / microstructure", "last-Friday 08:00 UTC reversal around Deribit expiry, half weight"),
    "delev bounce": ("crypto_sleeves.delev_bounce_weights", "mean reversion", "long BTC/ETH after a >10% open-interest drop with a price fall"),
    "ridge ML": ("ridge_live.ridge_weights(kb, volscale, spot, vrp, cal)", "machine learning", "monthly walk-forward ridge on 17+ daily features, BTC/ETH"),
    "alt kimchi": ("basket_live.altk_ensemble", "cross-exchange premium", "Upbit KRW premium z on 16 altcoins, thresholds 0.75/1/1.25"),
    "diversifier basket": ("basket_live.basket", "multi-signal basket", "8 BTC/ETH signals (USDT premium, mint shock, options flow, kimchi, ...)"),
    "relative crowding 6": ("basket_live.rc_pnl", "positioning", "market-neutral long/short-ratio crowding on 6 majors"),
    "listing short": ("event_live.pnl (Gen468 + Gen472 Bybit filter)", "event", "short new listings (crowding-sized) and Binance spot-delisting announcements"),
}


def strategies(c: sqlite3.Connection) -> dict:
    n = 0
    for name, (code, fam, desc) in SLEEVES_V98.items():
        key = "crypto:" + name.replace(" ", "_").replace("*", "star").lower()
        RG.upsert_strategy(c, key, name, "crypto_futures", fam, desc)
        vid = RG.add_version(c, key, "v9.8", "scripts/" + code.split(".")[0] + ".py :: " + code, {"book": "v9.8", "sleeve": name}, state="paper_trading",
                             notes="frozen with the v9.8 paper baseline (config/v98_freeze.json)")
        n += 1
    RG.add_portfolio_version(c, "crypto_book", "crypto_futures", "v9.8", list(SLEEVES_V98),
                             {"method": "equal risk (0.10 / trailing-365-day vol per sleeve, monthly), Weiss at half weight", "vol_target": 0.15,
                              "vol_window_days": 30, "leverage_cap": 1.5, "code": "crypto_sleeves.portfolio_v5"},
                             {"frequency": "hourly book, daily sleeve weights"}, state="paper_trading", purpose="HyroTrader / CFT crypto prop accounts",
                             notes="paper: QPL_PAPER=v98; reference backtest 3.211 [3.083, 3.849, 2.661]; planning about 1.64-1.71")
    RG.upsert_strategy(c, "futures:book", "Futures book (15 sleeves)", "futures", "trend / carry / calendar", "Gen205-238 futures book (ES, NQ, Treasuries, commodities)")
    RG.add_version(c, "futures:book", "gen238", "scripts/gen23x futures scripts", {"book": "futures", "ref": "Gen238"}, state="validation",
                   notes="2022-26 Sharpe about 1.24 (Gen435), needs a futures firm allowing overnight holding and bots")
    RG.upsert_strategy(c, "cfd:bf26", "BrightFunded CFD book bf2.6", "cfd", "crypto CFDs + index CFDs", "MT5 CFD version of the crypto book")
    RG.add_version(c, "cfd:bf26", "bf2.6", "scripts/cfd_book.py", {"book": "bf26"}, state="rejected",
                   notes="contains the withdrawn carry sleeves; honest version about 2.3 (Gen377); not in the plan")
    return {"crypto_sleeves": n}


def paper_accounts(c: sqlite3.Connection, base: Path = ROOT / "paper_trading") -> dict:
    out = {}
    for d in sorted(p for p in base.iterdir() if p.is_dir() and (p / "ledger_hourly.csv").exists()):
        ver = d.name; cfgp = ROOT / f"config/paper_{ver}.json"
        cfg = json.loads(cfgp.read_text()) if cfgp.exists() else {}
        acct = float(cfg.get("frozen", {}).get("account", 200_000))
        r = c.execute("SELECT id FROM paper_accounts WHERE key=?", (f"paper:{ver}",)).fetchone()
        with tx(c):
            aid = r["id"] if r else c.execute("INSERT INTO paper_accounts (key, source_dir, initial_capital, status, config, created_at) VALUES (?,?,?,?,?,?)",
                                              (f"paper:{ver}", str(d.relative_to(ROOT)), acct, "unknown", json.dumps(cfg.get("frozen", {})), now())).lastrowid
        L = pd.read_csv(d / "ledger_hourly.csv")
        risk = float(cfg.get("frozen", {}).get("risk", 1.0))
        L["ret"] = L["port"].astype(float) * risk
        eq = acct * (1 + L["ret"]).cumprod()
        sleeves = [s for s in L.columns if s not in ("hour", "port", "computed_at", "lag_h", "late") and not s.startswith("w ")]
        with tx(c):
            c.executemany("INSERT OR IGNORE INTO paper_equity (account_id, ts, ret, equity, late) VALUES (?,?,?,?,?)",
                          [(aid, h, float(x), float(e), int(str(lt) == "True")) for h, x, e, lt in zip(L["hour"], L["ret"], eq, L.get("late", [False] * len(L)))])
            rows = []
            for s in sleeves:
                w = L.get("w " + s)
                rows += [(aid, h, s, float(p), float(wv) if w is not None else None) for h, p, wv in zip(L["hour"], L[s], w if w is not None else [None] * len(L))]
            c.executemany("INSERT OR IGNORE INTO paper_sleeve_pnl (account_id, ts, sleeve, pnl, weight) VALUES (?,?,?,?,?)", rows)
            if (d / "orders.csv").exists():
                O = pd.read_csv(d / "orders.csv")
                c.executemany("INSERT OR IGNORE INTO paper_orders (account_id, ts, coin, side, usd, from_usd, to_usd, type, reason) VALUES (?,?,?,?,?,?,?,?,?)",
                              [tuple([aid] + [None if pd.isna(v) else v for v in row]) for row in O[["hour_utc", "coin", "side", "usd", "from_usd", "to_usd", "type", "because"]].itertuples(index=False)])
            if (d / "events.jsonl").exists():
                ev = [json.loads(x) for x in (d / "events.jsonl").read_text().splitlines() if x.strip()]
                c.executemany("INSERT OR IGNORE INTO paper_events (account_id, ts, event, details) VALUES (?,?,?,?)",
                              [(aid, e.get("wall_utc"), e.get("event"), json.dumps(e)) for e in ev])
            last = L["hour"].iloc[-1] if len(L) else None
            c.execute("UPDATE paper_accounts SET last_ingested_at=?, last_data_ts=? WHERE id=?", (now(), last, aid))
            audit(c, "ingest", "paper_account", "paper_accounts", aid, {"version": ver, "hours": len(L)})
        out[ver] = {"hours": len(L), "last": last}
    return out


DATA_DIRS = {"research_data/binance": ("crypto_futures", "Binance 5-min pack (20 perps)"), "research_data/binance_extra": ("crypto_futures", "40 extra perps, hourly"),
             "research_data/binance_pit": ("crypto_futures", "point-in-time perps incl. delisted, hourly"), "research_data/upbit": ("crypto_spot", "Upbit KRW hourly"),
             "research_data/coinbase": ("crypto_spot", "Coinbase USD hourly"), "research_data/bybit_listings": ("crypto_futures", "Bybit listings first 40 days"),
             "research_data/binance_announcements": ("events", "Binance announcement titles"), "research_data/okx_listings": ("crypto_futures", "OKX listings"),
             "data/processed": ("mixed", "processed research cache (local only)"), "data/lab": ("mixed", "Binance vision archive cache (local only)")}


def datasets(c: sqlite3.Connection) -> dict:
    out = {}
    for rel, (market, kind) in DATA_DIRS.items():
        p = ROOT / rel
        if not p.exists():
            status, n, b, last = "missing", 0, 0, None
        else:
            files = [f for f in p.rglob("*") if f.is_file()]
            n = len(files); b = sum(f.stat().st_size for f in files)
            last = pd.Timestamp(max((f.stat().st_mtime for f in files), default=0), unit="s").isoformat() if files else None
            status = "ok" if n else "empty"
        with tx(c):
            c.execute("INSERT INTO datasets (key, path, market, kind, n_files, bytes, last_ts, checked_at, status) VALUES (?,?,?,?,?,?,?,?,?) "
                      "ON CONFLICT(key) DO UPDATE SET n_files=excluded.n_files, bytes=excluded.bytes, last_ts=excluded.last_ts, checked_at=excluded.checked_at, status=excluded.status",
                      (rel, rel, market, kind, n, b, last, now(), status))
        out[rel] = {"files": n, "status": status}
    return out


def all_sources(c: sqlite3.Connection) -> dict:
    return {"legacy": legacy_registry(c), "protocols": protocols(c), "strategies": strategies(c), "paper": paper_accounts(c), "datasets": datasets(c)}
