"""v9.9 candidate DRY-RUN target book (task 70, user-approved 2026-11-02 as 'option a': prepare the bot; NOT activated in any paper account).

Builds paper_trading/v99cand/book_next_hour.json for the best candidate 'v99cand:all_plus_add_hodler' = v9.8 + four separate event
sleeves (Coinbase/Upbit sell-the-news, Binance futures-delisting, Binance 'add', HODLer airdrop), combined with exactly the composite
rule of the hub shadow (qpl.hub.shadow._composite: crypto_sleeves.portfolio_v5 over the v9.8 paper ledger + the event ledgers, each with
its research prefix, times the v9.8 scale). It only READS the v9.8 paper files; v9.8 and its paper validation are untouched.

Per coin and sleeve:
  v9.8 sleeves   usd_99 = usd_98 (book by_sleeve_usd) * eff_99[s] / eff_98[s]     (eff_98 = the v9.8 book's own sleeve_multipliers)
  event sleeves  usd_99 = position (-0.05 per open short, coinbase_short.position_at) * eff_99[s] * equity * risk
The book carries 'lowcap_sleeves' so the v9.9 bot runner (qpl.bot.runner_v99) applies the HyroTrader low-cap caps (5% per coin, 4.5% of
the initial balance in TOTAL) to every event-short coin. made_at_utc is the v9.8 book's (the stale-book guard follows the source).

    python -m qpl.live.v99_book            # one build (run after the v9.8 paper step and the hub's cbshort_paper job)"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "paper_trading/v98"
OUT = ROOT / "paper_trading/v99cand"
CANDIDATE = "v99cand:all_plus_add_hodler"
EVENT = {"venue listing short": ("venueshort", "results/v99/venueshort_sleeve_prefix.parquet"),
         "futures-delisting short": ("fdshort", "results/v99/fdshort_sleeve_prefix.parquet"),
         "binance add short": ("addshort", "results/v99/addshort_sleeve_prefix.parquet"),
         "hodler short": ("hodlershort", "results/v99/hodlershort_sleeve_prefix.parquet")}
LOWCAP = ["listing short", *EVENT]
V98_PREFIX = ROOT / "results/v98_paper_sleeves.parquet"
V98_OCT = ROOT / "results/v98_oct_oos.parquet"          # the v9.8 sleeves recomputed on the live data to 30 Oct 2026 (oos_october_v98.bat):
                                                        # closes the October gap between the research pack and the paper start


def _ledger(f: Path, cols: list[str]) -> pd.DataFrame:
    L = pd.read_csv(f, parse_dates=["hour"]).drop_duplicates("hour", keep="first").set_index("hour").sort_index()
    return L.reindex(columns=cols).astype(float).fillna(0.0)


def sleeve_hours(root: Path = ROOT) -> pd.DataFrame:
    """Hourly sleeve returns as the hub composite sees them: research prefix before the v9.8 paper start, then the frozen paper ledgers."""
    f = root / V98_OCT.relative_to(ROOT)
    pre = pd.read_parquet(f if f.exists() else root / V98_PREFIX.relative_to(ROOT)).drop(columns=["port"], errors="ignore")
    sl = list(pre.columns)
    P = _ledger(root / "paper_trading/v98/ledger_hourly.csv", sl)
    H = pd.concat([pre[pre.index < P.index[0]], P])
    for name, (d, prefix) in EVENT.items():
        f = root / "paper_trading" / d / "ledger_hourly.csv"
        col = _ledger(f, ["port"])["port"] if f.exists() else pd.Series(dtype=float)
        px = pd.read_parquet(root / prefix).iloc[:, 0]
        col = pd.concat([px[px.index < col.index.min()] if len(col) else px, col])
        H[name] = col.reindex(H.index).fillna(0.0)
    return H


def multipliers(H: pd.DataFrame, h1: pd.Timestamp, scale: float) -> pd.Series:
    """effective sleeve multipliers for hour h1 (weight * level/vol multiplier * scale), as paper_v5 computes them for v9.8."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import crypto_sleeves as CS
    Hx = pd.concat([H.loc[:h1 - pd.Timedelta(hours=1)], pd.DataFrame(0.0, index=[h1], columns=H.columns)])
    _, W, mult = CS.portfolio_v5(Hx, start=str(Hx.index[0].date()))
    d = h1.floor("D")
    return W.loc[d] * mult.get(d, np.nan) * scale if d in W.index else pd.Series(np.nan, index=H.columns)


def build(root: Path = ROOT, write: bool = True) -> dict:
    book = json.loads((root / "paper_trading/v98/book_next_hour.json").read_text())
    h1 = pd.Timestamp(book["for_hour_utc"]); eq, risk = float(book["equity"]), float(book["risk"])
    scale = json.loads((root / "config/paper_v98.json").read_text())["frozen"].get("v98_scale", 1.0)
    H = sleeve_hours(root); e99 = multipliers(H, h1, scale)
    e98 = {k: v for k, v in (book.get("sleeve_multipliers") or {}).items()}
    warn = []
    by: dict[str, dict[str, float]] = {}
    for coin, row in (book.get("by_sleeve_usd") or {}).items():
        for s, usd in row.items():
            m98, m99 = e98.get(s), e99.get(s, np.nan)
            if not m98 or not np.isfinite(m99):
                warn.append(f"{coin}/{s}: no multiplier (v9.8 {m98}, v9.9 {m99}) - left out"); continue
            by.setdefault(coin, {})[s] = round(usd * m99 / m98, 2)
    stale = []
    for name, (d, _) in EVENT.items():
        f = root / "paper_trading" / d / "open_positions.json"
        if not f.exists():
            warn.append(f"{name}: no open_positions.json yet (hub job cbshort_paper) - treated as flat"); continue
        op = json.loads(f.read_text())
        if pd.Timestamp(op["for_hour_utc"]) != h1:
            stale.append(name); warn.append(f"{name}: positions are for {op['for_hour_utc']}, book is for {h1} - treated as flat")
            continue
        for coin, pos in op["positions"].items():
            m = e99.get(name, np.nan)
            if np.isfinite(m) and pos:
                by.setdefault(coin, {})[name] = round(float(pos) * m * eq * risk, 2)
    tgt = {c: round(sum(r.values()), 2) for c, r in by.items()}
    out = {"for_hour_utc": book["for_hour_utc"], "made_at_utc": book["made_at_utc"], "built_at_utc": str(pd.Timestamp.now(tz="UTC").tz_localize(None)),
           "data_cutoff_utc": book.get("data_cutoff_utc"), "equity": eq, "risk": risk, "candidate": CANDIDATE,
           "target_notional_usd": {c: v for c, v in sorted(tgt.items(), key=lambda x: x[1]) if abs(v) > 1e-6},
           "by_sleeve_usd": {c: {s: v for s, v in r.items() if abs(v) >= 0.01} for c, r in by.items()},
           "sleeve_multipliers": {k: (None if not np.isfinite(v) else round(float(v), 4)) for k, v in e99.items()},
           "v98_sleeve_multipliers": e98, "lowcap_sleeves": LOWCAP,
           "cascade_limit_orders": book.get("cascade_limit_orders") or [], "cascade_open_trades": book.get("cascade_open_trades") or [],
           "event_positions_stale": stale, "warnings": warn,
           "note": "v9.9 CANDIDATE, DRY-RUN ONLY - not a paper account, no order is sent anywhere; v9.8 paper validation is separate"}
    if write:
        o = root / "paper_trading/v99cand"; o.mkdir(parents=True, exist_ok=True)
        tmp = o / "book_next_hour.tmp"; tmp.write_text(json.dumps(out, indent=1)); tmp.replace(o / "book_next_hour.json")
    return out


if __name__ == "__main__":
    b = build()
    print(json.dumps({k: b[k] for k in ("for_hour_utc", "sleeve_multipliers", "warnings")}, indent=1))
    print("gross", round(sum(abs(v) for v in b["target_notional_usd"].values())), "coins", len(b["target_notional_usd"]))
