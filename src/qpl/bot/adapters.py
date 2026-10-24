"""Exchange adapters. DryRun keeps positions in a local state file and assumes fills at the reference price (no network).
Live adapters are deliberately NOT implemented here: they will read API keys only from environment variables on the user's PC,
after the paper gate and the firm's written confirmation (research/PLAN.md)."""
from __future__ import annotations


class Adapter:
    name = "base"

    def equity(self) -> float: ...
    def positions(self) -> dict[str, float]: ...
    def place_limit(self, coin: str, usd: float, ref_price: float | None, minutes: int) -> dict: ...
    def place_market(self, coin: str, usd: float) -> dict: ...
    def cancel_all(self) -> None: ...
    def flatten(self) -> list[dict]: ...


class DryRun(Adapter):
    """Paper execution: every order fills at once at its reference price; equity moves with the book's own hourly P&L if given."""
    name = "dryrun"

    def __init__(self, state: dict, initial_balance: float):
        self.s = state; self.s.setdefault("positions", {}); self.s.setdefault("equity", initial_balance)

    def equity(self) -> float:
        return float(self.s["equity"])

    def positions(self) -> dict[str, float]:
        return dict(self.s["positions"])

    def _fill(self, coin, usd, how):
        p = self.s["positions"]; p[coin] = round(p.get(coin, 0.0) + usd, 2)
        if abs(p[coin]) < 1e-6:
            p.pop(coin)
        return {"coin": coin, "usd": usd, "filled_usd": usd, "how": how}

    def place_limit(self, coin, usd, ref_price=None, minutes=15):
        return self._fill(coin, usd, f"limit {minutes} min (dry-run: assumed filled)")

    def place_market(self, coin, usd):
        return self._fill(coin, usd, "market")

    def cancel_all(self):
        return None

    def flatten(self):
        return [self.place_market(c, -v) for c, v in list(self.s["positions"].items())]


class Bybit(Adapter):
    name = "bybit"

    def __init__(self, *a, **k):
        raise NotImplementedError("Live Bybit execution is not built yet (by design): it comes after the paper GO and the firm's written OK. "
                                  "Keys will be read from the environment (BYBIT_API_KEY / BYBIT_API_SECRET) on your own PC only.")
