"""Export the contract specifications of every symbol in the running MT5 terminal to research_data/firm_specs/.
Uses the official MetaTrader5 Python package (pip install MetaTrader5). It only READS symbol data from the terminal that is
already logged in; no orders, no account numbers or passwords are written.

    python scripts/mt5_export_specs.py            # all symbols (crypto first)
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
try:
    import MetaTrader5 as mt5
except ImportError:
    sys.exit("MetaTrader5 package missing: run  pip install MetaTrader5  and try again")

if not mt5.initialize():
    sys.exit(f"Could not connect to MT5 ({mt5.last_error()}). Open the MT5 app, log in to the trial account, and run this again.")
acc = mt5.account_info()
company = (acc.company if acc else "unknown").replace(" ", "_").replace("/", "_")
server = (acc.server if acc else "unknown").replace(" ", "_").replace("/", "_")
lev = acc.leverage if acc else None
rows = []
for s in mt5.symbols_get() or []:
    mt5.symbol_select(s.name, True)
    i = mt5.symbol_info(s.name); t = mt5.symbol_info_tick(s.name)
    if i is None:
        continue
    bid = t.bid if t else None; ask = t.ask if t else None
    mid = (bid + ask) / 2 if bid and ask else None
    margin_1lot = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, s.name, 1.0, ask) if ask else None
    rows.append({"symbol": s.name, "path": i.path, "description": i.description, "digits": i.digits, "point": i.point,
                 "contract_size": i.trade_contract_size, "swap_mode": i.swap_mode, "swap_long": i.swap_long, "swap_short": i.swap_short,
                 "swap_rollover3days": i.swap_rollover3days, "margin_initial": i.margin_initial, "margin_1lot_usd": margin_1lot,
                 "volume_min": i.volume_min, "volume_max": i.volume_max, "trade_mode": i.trade_mode, "bid": bid, "ask": ask,
                 "spread_bp": (ask - bid) / mid * 1e4 if mid else None,
                 "notional_1lot_usd": mid * i.trade_contract_size if mid else None})
mt5.shutdown()
df = pd.DataFrame(rows)
df["is_crypto"] = df["path"].str.contains("crypt", case=False) | df["symbol"].str.contains("BTC|ETH|XRP|SOL|ADA|DOG|LNK|LINK|LTC|AVAX|DOT|BCH", case=False)
df["swap_usd_per_lot_day_if_points"] = df["swap_long"] * df["point"] * df["contract_size"]
df["swap_bp_per_day_if_points"] = df["swap_usd_per_lot_day_if_points"] / df["notional_1lot_usd"] * 1e4
df["leverage_from_margin"] = df["notional_1lot_usd"] / df["margin_1lot_usd"]
df = df.sort_values(["is_crypto", "symbol"], ascending=[False, True])
out = ROOT / "research_data" / "firm_specs"; out.mkdir(parents=True, exist_ok=True)
f = out / f"{company}_{server}_{datetime.now(timezone.utc):%Y%m%d_%H%M}.csv"
df.to_csv(f, index=False)
print(f"{len(df)} symbols, account leverage 1:{lev}, saved to {f}")
c = df[df["is_crypto"]]
print(f"\ncrypto symbols ({len(c)}):")
print(c[["symbol", "swap_mode", "swap_long", "swap_short", "swap_bp_per_day_if_points", "leverage_from_margin", "spread_bp"]].round(2).to_string(index=False))
