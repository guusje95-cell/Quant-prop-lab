"""BloFin venue (HyroTrader offers BloFin challenges; Bybit is restricted in the Netherlands). PUBLIC market data only, no keys,
no orders: instrument rules (contract value, lot size, minimum size) and best bid / ask from the BloFin open API, either the DEMO
environment that HyroTrader challenges run on or the live one.

    python -m qpl.bot.venue_blofin --book paper_trading/v98/book_next_hour.json [--env demo|live] [--account 200000]

checks every target position of the paper book: is the coin listed, how many contracts, rounding error, below the minimum size.
`BlofinPaper` is a paper adapter with the same interface as adapters.DryRun that rounds to BloFin lots, refuses unlisted coins and
fills at the BloFin bid / ask. Live execution stays NOT implemented (it needs the paper GO, the firm's written OK and keys on the PC)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests

from qpl.bot.adapters import Adapter

HOSTS = {"demo": "https://demo-trading-openapi.blofin.com", "live": "https://openapi.blofin.com"}


def _get(env: str, path: str, **params) -> list[dict]:
    r = requests.get(HOSTS[env] + path, params=params, timeout=20); r.raise_for_status(); j = r.json()
    if str(j.get("code")) != "0":
        raise RuntimeError(f"BloFin {path}: {j}")
    return j.get("data") or []


def instruments(env: str = "demo") -> dict[str, dict]:
    """base coin -> spec of its USDT linear perpetual (instId, contractValue, lotSize, minSize)"""
    out = {}
    for x in _get(env, "/api/v1/market/instruments"):
        if x.get("quoteCurrency") == "USDT" and x.get("instType") == "SWAP" and x.get("state") == "live":
            out[x["baseCurrency"]] = {"instId": x["instId"], "ct": float(x["contractValue"]), "lot": float(x["lotSize"]), "min": float(x["minSize"])}
    return out


def tickers(env: str = "demo") -> dict[str, tuple[float, float]]:
    return {x["instId"]: (float(x.get("bidPrice") or 0), float(x.get("askPrice") or 0)) for x in _get(env, "/api/v1/market/tickers")}


def _base(coin: str, spec: dict) -> str | None:
    for c in (coin, "1000" + coin, coin.replace("1000", "")):
        if c in spec:
            return c
    return None


def contracts(usd: float, price: float, s: dict) -> float:
    n = abs(usd) / (price * s["ct"]); n = round(n / s["lot"]) * s["lot"]
    return 0.0 if n < s["min"] else n


def check_book(book: dict, env: str = "demo", account: float | None = None) -> dict:
    spec, tk = instruments(env), tickers(env)
    scale = (account / book["equity"]) if account else 1.0
    rows, gross, ok_gross, err = [], 0.0, 0.0, 0.0
    for coin, usd in book["target_notional_usd"].items():
        usd *= scale; gross += abs(usd); b = _base(coin, spec)
        if b is None:
            rows.append({"coin": coin, "usd": round(usd, 2), "status": "NOT LISTED"}); continue
        s = spec[b]; bid, ask = tk.get(s["instId"], (0.0, 0.0)); px = 0.5 * (bid + ask)
        if px <= 0:
            rows.append({"coin": coin, "usd": round(usd, 2), "status": "no price"}); continue
        n = contracts(usd, px, s); filled = n * s["ct"] * px * (1 if usd > 0 else -1)
        rows.append({"coin": coin, "usd": round(usd, 2), "instId": s["instId"], "contracts": n, "usd_after_rounding": round(filled, 2),
                     "status": "ok" if n > 0 else "below minimum size"})
        if n > 0:
            ok_gross += abs(filled); err += abs(filled - usd)
    return {"env": env, "positions": len(rows), "tradable_share_of_gross": round(ok_gross / gross, 4) if gross else None,
            "rounding_error_share": round(err / gross, 5) if gross else None, "not_listed": [r["coin"] for r in rows if r["status"] == "NOT LISTED"], "rows": rows}


class BlofinPaper(Adapter):
    """Paper execution on BloFin terms: lot rounding, listed coins only, fills at the current bid (sells) / ask (buys)."""
    name = "blofin-paper"

    def __init__(self, state: dict, initial_balance: float, env: str = "demo"):
        self.s = state; self.s.setdefault("positions", {}); self.s.setdefault("equity", initial_balance); self.env = env
        self.spec, self.tk = instruments(env), tickers(env)

    def equity(self) -> float:
        return float(self.s["equity"])

    def positions(self) -> dict[str, float]:
        return dict(self.s["positions"])

    def _fill(self, coin, usd, how):
        b = _base(coin, self.spec)
        if b is None:
            return {"coin": coin, "usd": usd, "filled_usd": 0.0, "how": "refused: not listed on BloFin " + self.env}
        s = self.spec[b]; bid, ask = self.tk.get(s["instId"], (0.0, 0.0)); px = ask if usd > 0 else bid
        n = contracts(usd, px, s); f = round(n * s["ct"] * px * (1 if usd > 0 else -1), 2)
        p = self.s["positions"]; p[coin] = round(p.get(coin, 0.0) + f, 2)
        if abs(p[coin]) < 1e-6:
            p.pop(coin)
        return {"coin": coin, "usd": usd, "filled_usd": f, "contracts": n, "price": px, "how": how}

    def place_limit(self, coin, usd, ref_price=None, minutes=15):
        return self._fill(coin, usd, f"limit {minutes} min (paper: assumed filled at the touch)")

    def place_market(self, coin, usd):
        return self._fill(coin, usd, "market")

    def cancel_all(self):
        return None

    def flatten(self):
        return [self.place_market(c, -v) for c, v in list(self.s["positions"].items())]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--book", required=True); ap.add_argument("--env", default="demo", choices=list(HOSTS))
    ap.add_argument("--account", type=float, default=None)
    a = ap.parse_args()
    r = check_book(json.loads(Path(a.book).read_text()), a.env, a.account)
    print(json.dumps({k: v for k, v in r.items() if k != "rows"}, indent=1))
    for x in r["rows"]:
        if x["status"] != "ok":
            print(f"  {x['coin']:10s} {x['usd']:>12,.2f}  {x['status']}")


if __name__ == "__main__":
    main()
