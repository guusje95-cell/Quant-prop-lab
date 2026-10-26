"""Fixed execution and risk rules (Gen323 / Gen327 / Gen330 / Gen337b)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Rules:
    initial_balance: float = 200_000.0     # the prop account size
    risk_challenge: float = 1.5            # book risk in the challenge (Gen413: 1.5 beats 2.0 at planning-level Sharpe on both bootstrap windows)
    risk_funded: float = 1.5               # book risk once funded (Gen323 / Gen330)
    gross_cap_funded: float = 1.9          # funded: open notional <= 1.9 x initial balance (HyroTrader cap 2x)
    gross_cap_challenge: float = 0.0       # 0 = no cap in the challenge
    lowcap_cap_frac: float = 0.05          # v9.6 listing-short coins: |notional| <= 5% of the initial balance (HyroTrader low-cap / Innovation Zone rule)
    band_usd: float = 1000.0               # no-trade band per coin (Gen323 C)
    min_order_usd: float = 50.0            # never send smaller orders
    daily_stop_frac: float = 0.025         # flat for the rest of the UTC day at -2.5% of the initial balance from the day's start (50% of a 5% limit)
    limit_minutes: int = 15                # limit at the reference price for 15 min, then market (Gen337b)
    max_book_age_minutes: int = 50         # do not trade a book older than this (late book -> skip the hour, Gen331: 1 h late costs 0.18 Sharpe)
