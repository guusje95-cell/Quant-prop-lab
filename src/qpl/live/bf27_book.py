"""bf2.7 CFD candidate DRY-RUN target book (C1, user-approved shadow; NOT a paper account, bf2.6 unchanged).

Builds paper_trading/bf27cand/book_next_hour.json = bf2.6 WITHOUT its two carry sleeves + relative crowding 6 CFD + diversifier basket CFD,
combined with exactly the hub composite rule of 'bf27cand:honest_plus_rc6_basket' (crypto_sleeves.portfolio_v5 over the bf2.6 paper
ledger with its research / October prefix and the two CFD sleeve ledgers with theirs, times the bf2.6 scale). Only READS bf2.6 files.

  bf2.6 sleeves   usd = usd_bf26 (book by_sleeve_usd) * eff_27[s] / eff_26[s]      (carry sleeves dropped)
  CFD sleeves     usd = position (paper_trading/rc6cfd|basketcfd/open_positions.json) * eff_27[s] * equity * risk

    python -m qpl.live.bf27_book"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
EXTRA = {"rc6 CFD": ("rc6cfd", "results/v99/rc6cfd_sleeve_prefix.parquet"), "basket CFD": ("basketcfd", "results/v99/basketcfd_sleeve_prefix.parquet")}
DROP = ("premium carry", "premium carry BF")


def _ledger(f: Path, cols: list[str]) -> pd.DataFrame:
    L = pd.read_csv(f, parse_dates=["hour"]).drop_duplicates("hour", keep="first").set_index("hour").sort_index()
    return L.reindex(columns=cols).astype(float).fillna(0.0)


def sleeve_hours(root: Path = ROOT) -> pd.DataFrame:
    pre_f = next((root / f for f in ("results/bf26_oct_oos.parquet", "results/bf26_paper_sleeves.parquet") if (root / f).exists()))
    pre = pd.read_parquet(pre_f).drop(columns=["port"], errors="ignore")
    sl = list(pre.columns); P = _ledger(root / "paper_trading/bf26/ledger_hourly.csv", sl)
    H = pd.concat([pre[pre.index < P.index[0]], P])
    H = H.drop(columns=[c for c in DROP if c in H])
    for name, (d, prefix) in EXTRA.items():
        f = root / "paper_trading" / d / "ledger_hourly.csv"
        col = _ledger(f, ["port"])["port"] if f.exists() else pd.Series(dtype=float)
        px = pd.read_parquet(root / prefix).iloc[:, 0]
        col = pd.concat([px[px.index < col.index.min()] if len(col) else px, col])
        H[name] = col.reindex(H.index).fillna(0.0)
    return H


def multipliers(H: pd.DataFrame, h1: pd.Timestamp, scale: float) -> pd.Series:
    sys.path.insert(0, str(ROOT / "scripts"))
    import crypto_sleeves as CS
    Hx = pd.concat([H.loc[:h1 - pd.Timedelta(hours=1)], pd.DataFrame(0.0, index=[h1], columns=H.columns)])
    _, W, mult = CS.portfolio_v5(Hx, start=str(Hx.index[0].date()))
    d = h1.floor("D")
    return W.loc[d] * mult.get(d, np.nan) * scale if d in W.index else pd.Series(np.nan, index=H.columns)


def build(root: Path = ROOT, write: bool = True) -> dict:
    book = json.loads((root / "paper_trading/bf26/book_next_hour.json").read_text())
    h1 = pd.Timestamp(book["for_hour_utc"]); eq, risk = float(book["equity"]), float(book["risk"])
    scale = json.loads((root / "config/paper_bf26.json").read_text())["frozen"].get("bf26_scale", 1.0)
    e27 = multipliers(sleeve_hours(root), h1, scale); e26 = book.get("sleeve_multipliers") or {}
    by, warn, stale = {}, [], []
    for coin, row in (book.get("by_sleeve_usd") or {}).items():
        for s, usd in row.items():
            if s in DROP:
                continue
            m26, m27 = e26.get(s), e27.get(s, np.nan)
            if not m26 or not np.isfinite(m27):
                warn.append(f"{coin}/{s}: no multiplier (bf2.6 {m26}, bf2.7 {m27}) - left out"); continue
            by.setdefault(coin, {})[s] = round(usd * m27 / m26, 2)
    for name, (d, _) in EXTRA.items():
        f = root / "paper_trading" / d / "open_positions.json"
        if not f.exists():
            warn.append(f"{name}: no open_positions.json yet (hub job cfdx_paper) - treated as flat"); continue
        op = json.loads(f.read_text())
        if pd.Timestamp(op["for_hour_utc"]) != h1:
            stale.append(name); warn.append(f"{name}: positions are for {op['for_hour_utc']}, book is for {h1} - treated as flat"); continue
        m = e27.get(name, np.nan)
        for coin, pos in op["positions"].items():
            if np.isfinite(m) and pos:
                by.setdefault(coin, {})[name] = round(float(pos) * m * eq * risk, 2)
    tgt = {c: round(sum(r.values()), 2) for c, r in by.items()}
    out = {"for_hour_utc": book["for_hour_utc"], "made_at_utc": book["made_at_utc"], "built_at_utc": str(pd.Timestamp.now(tz="UTC").tz_localize(None)),
           "equity": eq, "risk": risk, "candidate": "bf27cand:honest_plus_rc6_basket",
           "target_notional_usd": {c: v for c, v in sorted(tgt.items(), key=lambda x: x[1]) if abs(v) > 1e-6},
           "by_sleeve_usd": {c: {s: v for s, v in r.items() if abs(v) >= 0.01} for c, r in by.items()},
           "sleeve_multipliers": {k: (None if not np.isfinite(v) else round(float(v), 4)) for k, v in e27.items()},
           "bf26_sleeve_multipliers": e26, "cascade_limit_orders": [], "event_positions_stale": stale, "warnings": warn,
           "note": "bf2.7 CANDIDATE, DRY-RUN ONLY - not a paper account, no order is sent anywhere; bf2.6 paper validation is separate"}
    if write:
        o = root / "paper_trading/bf27cand"; o.mkdir(parents=True, exist_ok=True)
        tmp = o / "book_next_hour.tmp"; tmp.write_text(json.dumps(out, indent=1)); tmp.replace(o / "book_next_hour.json")
    return out


if __name__ == "__main__":
    b = build()
    print(json.dumps({k: b[k] for k in ("for_hour_utc", "sleeve_multipliers", "warnings")}, indent=1))
    print("gross", round(sum(abs(v) for v in b["target_notional_usd"].values())), "coins", len(b["target_notional_usd"]))
