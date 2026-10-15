"""Hourly bars + open interest per coin for the cascade tests (import-safe helper)."""
import pandas as pd
from qpl.lab import binance_pack as B
CACHE = {}


def hourly(coin):
    if coin not in CACHE:
        h = B.k5(coin)
        df = pd.DataFrame({"c": h.close.resample("1h").last(), "lo": h.low.resample("1h").min(), "hi": h.high.resample("1h").max(),
                           "v": h.quote_volume.resample("1h").sum()})
        df["oi"] = B.metrics(coin)["sum_open_interest_value"].resample("1h").last().reindex(df.index)
        CACHE[coin] = df
    return CACHE[coin]
