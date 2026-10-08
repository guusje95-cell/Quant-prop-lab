"""Contract specifications (CME published specs) and cost assumptions.

FACT: multipliers / tick sizes are CME contract specifications.
ASSUMPTION: commissions are an all-in round-turn estimate representative of
prop-firm platforms (TopstepX / Rithmic / Tradovate pricing tiers, 2025-26);
slippage defaults to 1 tick per side on market and stop orders, 0 on limit
orders that are only filled when price trades *through* the limit.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Instrument:
    symbol: str
    name: str
    point_value: float      # USD per 1.0 price point per contract
    tick_size: float
    commission_rt: float    # USD per contract round turn (all-in estimate)
    slippage_ticks: float = 1.0   # per side, market/stop orders
    proxy: str | None = None      # development-data proxy symbol (Dukascopy)
    exchange_tz: str = "America/Chicago"

    @property
    def tick_value(self) -> float:
        return self.point_value * self.tick_size

    def cost_per_rt(self, cost_mult: float = 1.0, slip_mult: float = 1.0, sides_slipped: int = 2) -> float:
        """Round-turn cost in USD for one contract."""
        return cost_mult * self.commission_rt + slip_mult * self.slippage_ticks * sides_slipped * self.tick_value


INSTRUMENTS: dict[str, Instrument] = {
    # Equity index futures
    "ES": Instrument("ES", "E-mini S&P 500", 50.0, 0.25, 2.80, proxy="US500"),
    "MES": Instrument("MES", "Micro E-mini S&P 500", 5.0, 0.25, 0.74, proxy="US500"),
    "NQ": Instrument("NQ", "E-mini Nasdaq-100", 20.0, 0.25, 2.80, proxy="US100"),
    "MNQ": Instrument("MNQ", "Micro E-mini Nasdaq-100", 2.0, 0.25, 0.74, proxy="US100"),
    "YM": Instrument("YM", "E-mini Dow", 5.0, 1.0, 2.80, proxy="US30"),
    "MYM": Instrument("MYM", "Micro E-mini Dow", 0.5, 1.0, 0.74, proxy="US30"),
    "RTY": Instrument("RTY", "E-mini Russell 2000", 50.0, 0.10, 2.80, proxy=None),
    # Metals / energy
    "GC": Instrument("GC", "Gold", 100.0, 0.10, 3.10, proxy="XAUUSD"),
    "MGC": Instrument("MGC", "Micro Gold", 10.0, 0.10, 1.00, proxy="XAUUSD"),
    "SI": Instrument("SI", "Silver", 5000.0, 0.005, 3.10, proxy="XAGUSD"),
    "CL": Instrument("CL", "Crude Oil", 1000.0, 0.01, 3.00, proxy="BRENT"),
    "MCL": Instrument("MCL", "Micro Crude Oil", 100.0, 0.01, 1.00, proxy="BRENT"),
    # CFDs for FTMO-style accounts: point_value per 'unit' of 0.1 index points-dollar; costs as spread.
    # ASSUMPTION: FTMO US100.cash spread ~1.0-2.0 pts, modelled as 0.9 pt per side (1.8 pt round trip), no commission.
    "US100CFD": Instrument("US100CFD", "Nasdaq-100 CFD (FTMO-style)", 0.1, 0.01, 0.0, slippage_ticks=90.0, proxy="US100"),
    "US500CFD": Instrument("US500CFD", "S&P 500 CFD (FTMO-style)", 0.1, 0.01, 0.0, slippage_ticks=30.0, proxy="US500"),
    # FX futures
    "6E": Instrument("6E", "Euro FX", 125000.0, 0.00005, 3.00, proxy="EURUSD"),
    "M6E": Instrument("M6E", "E-Micro EUR/USD", 12500.0, 0.0001, 0.80, proxy="EURUSD"),
    "6B": Instrument("6B", "British Pound", 62500.0, 0.0001, 3.00, proxy="GBPUSD"),
    "6J": Instrument("6J", "Japanese Yen", 12500000.0, 0.0000005, 3.00, proxy="USDJPY"),
}

# Spot FX / CFD (FTMO-style accounts). Costs expressed in price units per round turn
# per unit notional: typical raw spread + commission (ASSUMPTION, FTMO-like terms:
# ~0.1-0.3 pip raw spread on majors + $5/lot round-turn commission = ~0.5 pip/lot).
SPOT_COST_PRICE_UNITS = {
    "EURUSD": 0.00007, "GBPUSD": 0.00010, "USDJPY": 0.008, "AUDUSD": 0.00008,
    "USDCAD": 0.00010, "USDCHF": 0.00010, "XAUUSD": 0.25, "XAGUSD": 0.025,
    "US500": 0.6, "US100": 1.8, "US30": 3.0, "DE40": 1.5, "BRENT": 0.04,
}


def get(symbol: str) -> Instrument:
    return INSTRUMENTS[symbol]
