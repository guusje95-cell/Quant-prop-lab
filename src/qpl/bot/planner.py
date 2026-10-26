"""Turn a target book into orders: scale to the account, gross cap, no-trade band, closes. Pure functions (unit-tested)."""
from __future__ import annotations


def scaled_targets(book: dict, equity: float, risk: float) -> dict[str, float]:
    """The paper book is in USD at the paper's equity and risk; rescale to this account's equity and risk."""
    k = (equity * risk) / (float(book["equity"]) * float(book["risk"]))
    return {c: v * k for c, v in book["target_notional_usd"].items()}


def apply_cap(targets: dict[str, float], cap_usd: float) -> dict[str, float]:
    """Scale every target down proportionally when gross notional exceeds cap_usd (cap_usd <= 0: no cap)."""
    g = sum(abs(v) for v in targets.values())
    if cap_usd <= 0 or g <= cap_usd:
        return dict(targets)
    f = cap_usd / g
    return {c: v * f for c, v in targets.items()}


def cap_listing_coins(targets: dict[str, float], book: dict, cap_usd: float) -> dict[str, float]:
    """v9.6: coins traded by the listing short (book by_sleeve_usd) are capped at cap_usd in absolute notional (firm low-cap rule)."""
    lst = {c for c, row in (book.get("by_sleeve_usd") or {}).items() if abs(row.get("listing short", 0.0)) > 0}
    return {c: (max(-cap_usd, min(cap_usd, v)) if c in lst and cap_usd > 0 else v) for c, v in targets.items()}


def plan_orders(targets: dict[str, float], positions: dict[str, float], band_usd: float, min_order_usd: float) -> list[dict]:
    """Orders (USD notional, signed) to move positions toward targets. A coin trades only if |target - position| >= band, or its target is
    zero while a position is open (always close). Same rule as the research execution (Gen323 run(), Gen327 sim())."""
    out = []
    for c in sorted(set(targets) | set(positions)):
        t, p = targets.get(c, 0.0), positions.get(c, 0.0)
        d = t - p
        close = abs(t) < 1e-9 and abs(p) >= min_order_usd
        if (abs(d) >= band_usd or close) and abs(d) >= min_order_usd:
            out.append({"coin": c, "usd": round(d, 2), "side": "BUY" if d > 0 else "SELL", "from": round(p, 2), "to": round(t, 2), "close": close})
    return out
