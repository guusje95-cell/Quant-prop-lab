"""bf2.8 CFD candidate DRY-RUN target book (C10, user-approved shadow 'bf28cand:weiss_full_ensembles'; NOT a paper account, bf2.6
unchanged). Added 2026-11-10 (audit A-1): until then the MT5 bridge traded the older bf2.7 book (qpl.live.bf27_book).

bf2.8 = bf2.6 WITHOUT the two carry sleeves and WITHOUT its single-member trend 4h / alt kimchi, PLUS relative crowding 6 CFD, diversifier
basket CFD and the Gen383 ensembles 'trend 4h ens CFD' / 'alt kimchi ens CFD' (paper_trading/{rc6cfd,basketcfd,trendcfd,altkcfd}), with
Weiss expiry at FULL equal-risk weight; combined with exactly the hub composite rule of the shadow (crypto_sleeves.portfolio_v5 with
weiss_scale 1.0 over the bf2.6 paper ledger + the four CFD ledgers with their research prefixes, times the bf2.6 scale).

  kept bf2.6 sleeves  usd = usd_bf26 (book by_sleeve_usd) * eff_28[s] / eff_26[s]
  CFD sleeves         usd = position (paper_trading/<dir>/open_positions.json) * eff_28[s] * equity * risk
The 4x cap on the Weiss contribution is applied by the MT5 bridge's 1:5 crypto cap.

    python -m qpl.live.bf28_book"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from qpl.live import bf27_book as B27

ROOT = Path(__file__).resolve().parents[3]
CANDIDATE = "bf28cand:weiss_full_ensembles"
EXTRA = {"rc6 CFD": ("rc6cfd", "results/v99/rc6cfd_sleeve_prefix.parquet"), "basket CFD": ("basketcfd", "results/v99/basketcfd_sleeve_prefix.parquet"),
         "trend 4h ens CFD": ("trendcfd", "results/v99/trendenscfd_sleeve_prefix.parquet"),
         "alt kimchi ens CFD": ("altkcfd", "results/v99/altkenscfd_sleeve_prefix.parquet")}
DROP = ("premium carry", "premium carry BF", "trend 4h", "alt kimchi")
OUT = ROOT / "paper_trading/bf28cand"


def sleeve_hours(root: Path = ROOT) -> pd.DataFrame:
    pre_f = next((root / f for f in ("results/bf26_oct_oos.parquet", "results/bf26_paper_sleeves.parquet") if (root / f).exists()))
    pre = pd.read_parquet(pre_f).drop(columns=["port"], errors="ignore")
    sl = list(pre.columns); P = B27._ledger(root / "paper_trading/bf26/ledger_hourly.csv", sl)
    H = pd.concat([pre[pre.index < P.index[0]], P])
    H = H.drop(columns=[c for c in DROP if c in H])
    for name, (d, prefix) in EXTRA.items():
        f = root / "paper_trading" / d / "ledger_hourly.csv"
        col = B27._ledger(f, ["port"])["port"] if f.exists() else pd.Series(dtype=float)
        px = pd.read_parquet(root / prefix).iloc[:, 0]
        col = pd.concat([px[px.index < col.index.min()] if len(col) else px, col])
        H[name] = col.reindex(H.index).fillna(0.0)
    return H


def multipliers(H: pd.DataFrame, h1: pd.Timestamp, scale: float) -> pd.Series:
    sys.path.insert(0, str(ROOT / "scripts"))
    import crypto_sleeves as CS
    Hx = pd.concat([H.loc[:h1 - pd.Timedelta(hours=1)], pd.DataFrame(0.0, index=[h1], columns=H.columns)])
    orig = CS.v5_weights
    CS.v5_weights = lambda D, sleeves, weiss_scale=0.5: orig(D, sleeves, weiss_scale=1.0)       # bf2.8: Weiss at full weight
    try:
        _, W, mult = CS.portfolio_v5(Hx, start=str(Hx.index[0].date()))
    finally:
        CS.v5_weights = orig
    d = h1.floor("D")
    return W.loc[d] * mult.get(d, np.nan) * scale if d in W.index else pd.Series(np.nan, index=H.columns)


def build(root: Path = ROOT, write: bool = True) -> dict:
    book = json.loads((root / "paper_trading/bf26/book_next_hour.json").read_text())
    h1 = pd.Timestamp(book["for_hour_utc"]); eq, risk = float(book["equity"]), float(book["risk"])
    scale = json.loads((root / "config/paper_bf26.json").read_text())["frozen"].get("bf26_scale", 1.0)
    e28 = multipliers(sleeve_hours(root), h1, scale); e26 = book.get("sleeve_multipliers") or {}
    by, warn, stale = {}, [], []
    for coin, row in (book.get("by_sleeve_usd") or {}).items():
        for s, usd in row.items():
            if s in DROP:
                continue
            m26, m28 = e26.get(s), e28.get(s, np.nan)
            if not m26 or not np.isfinite(m28):
                warn.append(f"{coin}/{s}: no multiplier (bf2.6 {m26}, bf2.8 {m28}) - left out"); continue
            by.setdefault(coin, {})[s] = round(usd * m28 / m26, 2)
    for name, (d, _) in EXTRA.items():
        f = root / "paper_trading" / d / "open_positions.json"
        if not f.exists():
            warn.append(f"{name}: no open_positions.json yet (hub job cfdx_paper) - treated as flat"); stale.append(name); continue
        op = json.loads(f.read_text())
        if pd.Timestamp(op["for_hour_utc"]) != h1:
            stale.append(name); warn.append(f"{name}: positions are for {op['for_hour_utc']}, book is for {h1} - treated as flat"); continue
        m = e28.get(name, np.nan)
        for coin, pos in op["positions"].items():
            if np.isfinite(m) and pos:
                by.setdefault(coin, {})[name] = round(float(pos) * m * eq * risk, 2)
    tgt = {c: round(sum(r.values()), 2) for c, r in by.items()}
    out = {"for_hour_utc": book["for_hour_utc"], "made_at_utc": book["made_at_utc"], "built_at_utc": str(pd.Timestamp.now(tz="UTC").tz_localize(None)),
           "equity": eq, "risk": risk, "candidate": CANDIDATE,
           "target_notional_usd": {c: v for c, v in sorted(tgt.items(), key=lambda x: x[1]) if abs(v) > 1e-6},
           "by_sleeve_usd": {c: {s: v for s, v in r.items() if abs(v) >= 0.01} for c, r in by.items()},
           "sleeve_multipliers": {k: (None if not np.isfinite(v) else round(float(v), 4)) for k, v in e28.items()},
           "bf26_sleeve_multipliers": e26, "cascade_limit_orders": [], "event_positions_stale": stale, "warnings": warn,
           "note": "bf2.8 CANDIDATE, DRY-RUN ONLY - not a paper account, no order is sent anywhere; bf2.6 paper validation is separate"}
    if write:
        OUT.mkdir(parents=True, exist_ok=True)
        tmp = OUT / "book_next_hour.tmp"; tmp.write_text(json.dumps(out, indent=1)); tmp.replace(OUT / "book_next_hour.json")
    return out


if __name__ == "__main__":
    b = build()
    print(json.dumps({k: b[k] for k in ("for_hour_utc", "sleeve_multipliers", "warnings")}, indent=1))
    print("gross", round(sum(abs(v) for v in b["target_notional_usd"].values())), "coins", len(b["target_notional_usd"]))
